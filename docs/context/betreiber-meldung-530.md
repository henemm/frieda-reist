# Context: Rückmeldung an den Betreiber aus der Claude-App (#530, Teil von #384)

## Request Summary
Tester melden Fehler, Wünsche und Fragen zu Frieda selbst direkt in der Claude-App über ein Konto-Werkzeug
(`report_to_frieda`, Alias `an_frieda_melden`). Die Meldung wird in der Kontendatenbank abgelegt, alle Betreiber bekommen
eine Mail mit Antwortadresse des Testers, Betreiber sehen offene Meldungen bei `my_trips`. Entscheidung des Product Owners
vom 12.11.2026 (Weg A, Kommentar in #384); Plan im ersten Kommentar von #530.

## Ausgangslage
- Arbeitszweig `alpha-384-probelauf` auf den Stand von `main` mit Export (#498) gebracht.
- Entwurf als Patch außerhalb des Repos (`~/frieda-entwuerfe/530-entwurf.patch`): konnektor.py, konten.py, schnittstelle.py,
  texte_de.py, texte_en.py. konnektor/konten/schnittstelle passen glatt; texte_de/en scheitern nur an einer Kontextzeile
  (`recht.datenschutz.folgt`, die der Export inzwischen geändert hat). Diese Zeile bleibt, wie sie auf `main` steht.

## Related Files
| File | Relevance |
|------|-----------|
| engine/konten.py | SCHEMA (neue Tabelle `betreiber_meldungen`), `mail_senden` (neuer Parameter `antwort_an` → Reply-To), `_begrenzt`/`versand` (Tagesgrenze), `loeschen(kid)` (Zeilen und Versand-Schlüssel `betreiber_meldung:<kid>` löschen), CLI (`meldungen`, `meldung-erledigt`) |
| engine/konnektor.py | `frieda_werkzeuge` (Konto-Werkzeug neben `kalender`, `sprache_setzen`), `frieda_werkzeug` (Behandlung vor der Reise-Auswahl), `meine_reisen_konto` (Betreiber-Liste), `anleitung_frieda` (Satz `frieda.melden`, im Patch noch nicht eingebaut) |
| engine/schnittstelle.py | NAMEN: `report_to_frieda` ↔ `an_frieda_melden`, Parameter `zusammenhang` → `context` |
| engine/anmeldung.py | `DATENSCHUTZ_ABSCHNITTE` (+ `betreiber_meldungen`), `alpha_inhalt` (+ Satz `recht.alpha.melden` mit Kontakt aus `FR_BETREIBER_KONTAKT`, sonst Link zum Impressum), `export_person` (+ eigene Meldungen in person.json) |
| engine/texte_de.py, texte_en.py (+ weitere texte_*.py, Pseudo-Sprache) | alle sichtbaren Texte |
| engine/instanz.py | `wert("FR_BETREIBER_KONTAKT")`; Betreiber-Konten über die Betreiber-Rolle in konten |
| docs/betrieb.md | Datenschutz-Tabelle („Quelle der Datenschutzerklärung“) + Betriebsbefehle |
| docs/konnektor.md, docs/konten.md | Werkzeugliste, Konto-Befehle |
| engine/tests/test_betreiber_meldung.py (neu) | RED-Tests |
| engine/tests/test_loeschen_konto.py | prüft über `sqlite_master`, dass keine Zeile des Kontos bleibt → deckt die neue Tabelle automatisch ab |
| engine/tests/test_export.py | Export der Kontoangaben |
| engine/tests/test_texte.py | Vollständigkeit aller Sprachen, Ausnahmelisten nur kürzer |

## Existing Patterns
- Konto-Werkzeuge ohne Reise: `kalender`, `sprache_setzen` in `frieda_werkzeuge`/`frieda_werkzeug` (vor der Reise-Auswahl).
- Tagesgrenze für Mails: `_begrenzt(schluessel, …)` mit Tabelle `versand` (wie `adresse:<email>`, `warteliste:<email>`).
- Betreiber-Hinweise bei `my_trips`: bisher Freischaltungs-Anfragen (`konto.betreiber.meldung`).
- Mail im Test: `FR_MAIL_DATEI` schreibt JSON-Zeilen (an, betreff, text); bekommt nun auch `antwort_an`.
- Rechtsseiten: Texte im Katalog, Betreiberangaben aus `FR_BETREIBER_*` (Impressum).
- Löschen des Kontos (#381): eine Transaktion über alle Tabellen mit Konto.
- Export (#498): `export_person` liefert nur Angaben des eigenen Kontos; Text `konto.export.punkt_4` beschreibt sie.

## Dependencies
- Upstream: SQLite-Kontendatenbank, SMTP (Resend) über `mail_senden`, Textkatalog, `instanz.wert`.
- Downstream: Claude-App (Werkzeugliste, Anleitung), Betreiber-Postfach, Datenschutzerklärung `/datenschutz`, Alpha-Hinweis `/alpha`, Export „Meine Daten herunterladen“, Konto löschen, Instanz-Tests im privaten Reisen-Repo (neue Texte/Schnittstelle → vor dem Vorspulen Instanz-Tests laufen lassen).

## Existing Specs
- docs/specs/konnektor/* (Konto-Werkzeuge), docs/specs/warteliste-382.md (Tagesgrenze, Betreiber-Liste), Specs zu #381 (Löschen) und #498 (Export).

## Risks & Considerations
- Mailkontingent Resend: 100/Tag gemeinsam; Grenze 10 Meldungen je Konto und Tag, Mailfehler dürfen die Meldung nicht verlieren.
- Testerdaten nie ins öffentliche Repo: Issues zu Meldungen nur im privaten Reisen-Repo.
- Export muss die eigenen Meldungen enthalten (Export verspricht „alles, was Frieda zu dir speichert“) – im Patch noch nicht.
- `recht.datenschutz.folgt` nicht anfassen (Export hat es schon angepasst).
- Neue sichtbare Texte (Datenschutz-Abschnitt, Alpha-Satz) → „Erst zeigen, dann bauen“: Entwurf vor dem Ausliefern als Artefakt.
- Werkzeug darf nicht in die Schreibgrenze zählen und keine fremde Reise annehmen.

## Für die Checkliste „Alpha-Start“ (Kommentar in #384, nach dem Ausliefern)
- Verweis auf den Kommentar „Betriebsnachweis Alpha“ von Spur A in #384 (Rückspielversuch 156 s und 141 s bestanden, Lastgrenzen, Ausfallmeldung, Resend 9–20 Mails je Tag).
- Entscheidung des Product Owners (12.11.2026, über Spur A): keine festen Tester. Er teilt einen LinkedIn-Beitrag mit Link zur Infoseite bzw. Warteliste. Folgen (Kommentar in #384) aufnehmen:
  #530 muss vorher live sein; Freigabe in kleinen Gruppen; Mailkontingent (Resend Free, etwa 25 Eintragungen je Tag, danach scheitern Mails aller Dienste; Frage dazu stellt Spur A dem PO);
  rechtliche Prüfung von Datenschutz und Impressum durch den Product Owner.

## Analysis

### Type
Feature (Entscheidung des Product Owners vom 12.11.2026, Weg A). Technischer Plan steht im ersten Kommentar von #530; der
Entwurf deckt Werkzeug, Ablage, Mail, Betreiberliste und CLI ab und wurde gegen den aktuellen Stand geprüft (nur die
Kontextzeile `recht.datenschutz.folgt` in texte_de/en weicht ab → beim Anwenden diese Zeile auf `main`-Stand lassen).

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/konten.py | MODIFY | Tabelle `betreiber_meldungen`, `BETREIBER_MELDUNG_ARTEN`, `an_betreiber_melden`, `betreiber_meldungen`, `betreiber_meldung_erledigt`, `eigene_betreiber_meldungen(kid)` (für den Export), `mail_senden(..., antwort_an=None)` mit Reply-To (auch in `FR_MAIL_DATEI`), `loeschen` (Tabelle über die Liste, Versand-Schlüssel), CLI `meldungen [--alle]`, `meldung-erledigt <nr> <issue>` |
| engine/konnektor.py | MODIFY | Konto-Werkzeug `an_frieda_melden` (reise optional als enum der eigenen Reisen), Behandlung in `frieda_werkzeug`, Betreiberliste in `meine_reisen_konto`, Satz `frieda.melden` in `anleitung_frieda` |
| engine/schnittstelle.py | MODIFY | `report_to_frieda` ↔ `an_frieda_melden`, `zusammenhang` → `context` |
| engine/anmeldung.py | MODIFY | `DATENSCHUTZ_ABSCHNITTE` + `betreiber_meldungen`; `alpha_inhalt` + Satz `recht.alpha.melden` mit Kontakt aus `FR_BETREIBER_KONTAKT`, ohne Kontakt Link zum Impressum; `export_person` + `betreiber_meldungen` (art, text, zusammenhang, reise, zeit, erledigt ja/nein; ohne Issue-Verweis) |
| engine/texte_de.py, engine/texte_en.py | MODIFY | Texte laut Entwurf + `konnektor.anleitung.frieda.melden`, `recht.alpha.melden` (mit `{kontakt}`), Export-Punkt 4 nennt die Meldungen |
| engine/tests/test_betreiber_meldung.py | CREATE | RED-Tests (siehe Spec) |
| docs/betrieb.md, docs/konnektor.md, docs/konten.md | MODIFY | Datenschutzzeile, Werkzeug, Befehle |

### Scope Assessment
- Files: 9 (davon 1 neu)
- Estimated LoC: +~350 / -~10 (inkl. Tests und Doku)
- Risk Level: MEDIUM – neue Mail an Betreiber über das gemeinsame Resend-Kontingent (Grenze 10 je Konto und Tag), Konto löschen und Export müssen die neue Tabelle mitnehmen; der Rest ist ein abgegrenztes Konto-Werkzeug.

### Technical Approach
Entwurf anwenden (texte-Hunks von Hand an die geänderte Kontextzeile anpassen), dann die offenen Stellen ergänzen:
anmeldung.py (Datenschutz, Alpha-Hinweis, Export), Anleitungssatz in `anleitung_frieda`, Export-Punkt 4.
Mailfehler: Meldung bleibt gespeichert, Tester bekommt „angekommen“, stderr-Zeile; der Betreiber sieht sie trotzdem bei
`my_trips` und mit `konten.py meldungen`. Betreiber = Konten mit Recht `betreiber` (wie Freischaltungen).
Sichtbare neue Texte (Datenschutz-Abschnitt, Alpha-Satz, Export-Punkt) vor dem Ausliefern als Entwurf im Artefakt zeigen
(Regel „Erst zeigen, dann bauen“); passt in die Freigabe nach der Spec.
Vor dem Vorspulen: Instanz-Tests im privaten Reisen-Repo mit dem Branch (neue Texte und Schnittstelle).

### Dependencies
konten.db (SQLite, CREATE IF NOT EXISTS → keine Umstellung in `neu.py nachziehen` nötig, keine Reisedaten betroffen),
SMTP über `mail_senden`, `instanz.wert("FR_BETREIBER_KONTAKT")`, Textkatalog; Konnektor-Modulliste in `betrieb/deploy.sh`
unverändert (kein neues Modul).

### Open Questions
- keine Produktfrage offen; die Texte zeigt Claude bei der Freigabe der Spec.
