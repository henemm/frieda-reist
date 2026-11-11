# Context: alpha-381-loeschen (#381 Löschen von Reise und Konto)

## Request Summary
Für die Alpha (M5a) soll eine Organisator:in eine Reise selbst löschen können (Mein Konto, doppelte Bestätigung, 14 Tage
Schonfrist, danach endgültiges Entfernen aller Versionen, Fotos, GPX, Belege, Rückmeldungen) und jede Person ihr Konto
(„gelöschte Person“ auch im Verlauf, Beiträge bleiben). Sicherungen spätestens nach 30 Tagen sauber. Export ist #498.

## Entscheidungen des Product Owners
- 10.11.2026 (Issue-Kommentar): Grundentscheidung 1–4, Export ausgelagert nach #498.
- 11.11.2026: Entwurf freigegeben (Link „Reise löschen …“ unter den aufgeklappten Personen, nur Organisator:innen;
  Bestätigung 1 mit Haken, Bestätigung 2 mit Eintippen des Reisenamens; Reise in Schonfrist oben in „Meine Reisen“ mit
  Datum und Knopf „Reise zurückholen“; E-Mail und Meldung an alle anderen Mitglieder sofort, beim Zurückholen eine
  zweite; Konto-Löschseite „Das bleibt, ohne deinen Namen“; Reisen, in denen nur die Person ist, gehen mit Schonfrist mit).
- 11.11.2026: Letzte Organisator:in einer Reise mit anderen Mitgliedern kann ihr Konto erst löschen, wenn die Rolle
  übergeben oder die Reise gelöscht ist („erst klären“).

## Related Files
| File | Relevance |
|------|-----------|
| engine/konten.py | Schema ab Z. 108; `loeschen(kid)` Z. 481 (räumt einladungen, angelegte_reisen, schreibvorgaenge, oauth_* nicht ab; Docstring „Verlauf behält Namen“); Mitgliedschaften Z. 729–797; `mail_senden` Z. 239 |
| engine/anmeldung.py | `konto_seite` Z. 691, `personen_block` Z. 659, `loeschen_seite` Z. 782, POST-Aktion `loeschen` ab Z. 1125; Datenschutzseite `DATENSCHUTZ_ABSCHNITTE` |
| engine/reisespeicher.py | Schema Z. 112–133 (vorgaenge.wer Klartextname, versionen), Trigger gegen UPDATE/DELETE, Authorizer `VERBOTEN` Z. 135 ff.; Ablage inhaltsadressiert Z. 200–290 (geteilte Dateien möglich); `reisen()` Z. 447 |
| engine/schreiben.py | Namen in Herkunftstexten und Verlauf der Reisedaten (Z. 332, 516, 2975, 3061, 4097) |
| engine/belege.py, Rückmeldungen | Ablage `<FR_ABLAGE>/<reise>/belege/`, Rückmeldungen/Aufgaben in der Ablage |
| engine/konnektor.py | `my_trips`, Archiv-Ausblendung Z. 2255; Löschwunsch-Anleitung `konnektor.anleitung.loeschwunsch` |
| engine/waechter.py, betrieb/waechter.sh | täglicher Lauf; Meldungen `neue_meldungen` Z. 329, `empfaenger` Z. 179 |
| betrieb/veroeffentlichen.sh | Speicherreisen Z. 222 (`speicher_reisen_lauf`), Git-Reisen Z. 196 |
| betrieb/sichern.sh, docs/betrieb.md | Schnappschüsse Z. 35–39, Datenschutz-Tabelle Z. 44–59, Belege „nie gelöscht“ Z. 118, Wächterlauf Z. 245 |
| engine/texte_de.py, texte_en.py (u. a.) | `konto.seite.loeschen_*` Z. 1103 ff., `recht.datenschutz.*` Z. 3518 ff. (Verlauf 3527, Belege 3529, Sicherungen 3531, Konto löschen 3537, folgt 3538) |
| engine/instanz.py | Vorgaben der Instanz (Frist 14 Tage hierher) |
| engine/tests/test_trennung.py, test_rechtliches.py | Vorbilder bzw. zu ergänzende Tests |

## Existing Patterns
- Archiv-Status (`trip_status_set` → archiv) blendet in Listen aus; Vorbild für die Anzeige, kein Löschmechanismus.
- Meldungen auf Mein Konto (docs/specs/oberflaeche/meldungen-konto-407.md), Mail über Resend (`mail_senden`), Push.
- Mengengrenzen je Konto (#380, `angelegte_reisen`, `schreibvorgaenge`).
- Specs unter `docs/specs/<bereich>/<name>-<issue>.md` (Vorbild `docs/specs/betrieb/rechtliches-383.md`).

## Dependencies
- Upstream: SQLite (konten.db, reisen.db), Ablage-Ordner, Resend-Mail, systemd-Timer des Wächters.
- Downstream: Seitenbau/Veröffentlichen, Konnektor, Rückmeldedienst, Sicherung, Export (#498, Sitzung frieda-reist-8c: soll Reisen in Schonfrist auslassen; Abgrenzung auf Mein Konto abgesprochen: Export-Abschnitt „Meine Daten“ und `konto.export.*` gehören #498).

## Existing Specs
- docs/specs/konnektor/loeschwunsch.md (Frieda löscht nie; auf Mein Konto verweisen)
- docs/specs/betrieb/rechtliches-383.md (Datenschutztext muss Verhalten entsprechen)
- docs/specs/oberflaeche/meldungen-konto-407.md
- docs/adr/0001-kern.md (Frage 7 Verlauf), 0005-konten.md, 0009-reisespeicher.md (nur anhängen)

## Plan (Teilschritte, je ≤5 Dateien)
C1 ADR-0001/0009 ergänzen → A Vormerken/Zurückholen (Tabelle `reise_loeschung` in konten.db, Mein Konto, beide
Bestätigungen) → A2 Unsichtbar (reisen(), Konnektor, Seitenbau, nginx) und Benachrichtigen → A3 endgültiges Entfernen im
täglichen Lauf → B Konto löschen mit Pseudonymisierung und Sperre letzte Organisator:in → C2 Datenschutztext, Betrieb.

## Risks & Considerations
- Echtes Entfernen in SQLite: Reste in freien Seiten/WAL → `wal_checkpoint(TRUNCATE)` + `VACUUM` nachts; Ausnahme fest
  im Code, nur diese eine Funktion umgeht Trigger/Authorizer; `pruefen` muss danach grün bleiben.
- Ablage inhaltsadressiert: nur Dateien entfernen, auf die keine andere Reise verweist.
- Pseudonymisieren schreibt alte Versionen lebender Reisen anderer um (zweite Ausnahme, Prüfsummen neu rechnen);
  Zuordnung über Personenschlüssel der Mitgliedschaft, nicht über Namenssuche; Namen in Freitexten nur näherungsweise.
- Sicherungen außer Haus: Software kann 30 Tage nicht erzwingen → Aufbewahrung des Server-Backups prüfen (henemm-infra);
  nach Rückspielen einer alten Sicherung muss der tägliche Lauf Gelöschtes erneut entfernen (Protokoll der Löschungen).
- Alte Git-Reisen (nicht im Speicher): Löschen nur für Speicherreisen; Git-Reisen bleiben Betreiber-Sache.
- Einladungen mit Adresse/Name, Wartelisten-Eintrag derselben Adresse beim Konto-Löschen mit aufräumen.
- Zeitangaben in Mails und Seiten mit Zone (Server UTC, Anzeige in der Zone der Person).
- Sichtbare Texte nur im Katalog, alle Sprachen; beide Beispielreisen testen.

## Analysis

### Type
Feature (Alpha M5a, Datenschutz: Löschen von Reise und Konto).

### Befunde aus dem Code (11.11.2026)
- Reisespeicher (`engine/reisespeicher.py`): Nur-Anhängen doppelt geschützt (Trigger Z. 125–132, Authorizer `_waechter` Z. 144, den `db()` Z. 157 immer setzt). `pruefsumme` ist SHA-256 über `inhalt`; ausgelagerte Medien liegen inhaltsadressiert in der Ablage (`ablage_pfad`, Modus 400), dieselbe Datei kann zu mehreren Reisen gehören. `sichern()` Z. 900 schreibt einen Schnappschuss nach `<Speicher>/sicherung/reisen.db`.
- Namen stehen an drei Orten: `vorgaenge.wer` (Verlauf), im **Inhalt** der Reisedateien (Herkunftstexte aus `engine/schreiben.py` Z. 332, 516, 2975, 3061, 4097, 4163, Fußzeile Z. 5176) und in Dateien der Ablage der Instanz (Rückmeldungen, Belege, Aufgaben unter `<FR_ABLAGE>/<reise>/`). Pseudonymisieren heißt daher: alte Versionen umschreiben, Prüfsummen neu rechnen, Neubau erzwingen (Stempel `.gebaut` hängt an der Stand-Nummer, nicht am Inhalt).
- `konten.loeschen` (Z. 481) räumt `einladungen`, `angelegte_reisen`, `schreibvorgaenge`, `oauth_*`, `warteliste` nicht ab; Docstring „Verlauf behält Namen“ widerspricht der Entscheidung. Der Personenschlüssel der Mitgliedschaft muss vor deren Löschung gelesen werden (Zuordnung der Beiträge).
- Kein Weg entfernt heute eine Reise aus Webordner (`<FR_SEITEN>/<reise>`), Bauordner (`<FR_DIENST>/bau/reisen/<reise>`) und Stempeln (`<FR_DIENST>/reise-stand/<reise>.*`); muss neu entstehen. nginx liefert statisch aus, eine entfernte Seite gibt 404.
- `waechter.alle_reisen()` (Z. 413) liest die Ablage, nicht den Speicher: Reisen in Schonfrist dort ausschließen (keine Erinnerungen).
- **Abhängigkeit Speicher-Umschaltung:** Endgültiges Entfernen geht nur für Reisen im Reisespeicher (`FR_SPEICHERREISEN`). Reisen auf dem alten Weg liegen mit Geschichte im privaten Reisen-Repo; dort ist echtes Entfernen ohne Umschreiben der Geschichte nicht möglich. Stufe 5 (#350, Umschaltung der Instanz) ist offen. Entscheidung Tech Lead: „Reise löschen“ nur für Speicherreisen; sonst erscheint der Link nicht (Satz: erst nach der Umstellung möglich). Vor dem Going Live muss #350 für alle Reisen der Alpha-Instanz erledigt sein und `reise_anlegen` neue Reisen direkt im Speicher anlegen (Prüfpunkt in der Spec, ggf. eigenes Issue).
- Export (#498, Sitzung 8c) bindet `konten.reise_vorgemerkt(reise) -> bool` an (abgesprochen 11.11.2026; Export liefert für vorgemerkte und entfernte Reisen 404), Abgrenzung der Texte auf Mein Konto bestätigt.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| docs/adr/0001-kern.md, docs/adr/0009-reisespeicher.md | MODIFY | Ausnahme vom Nur-Anhängen: nur Löschen einer Reise und Pseudonymisieren, fest im Code |
| engine/konten.py | MODIFY | Tabelle `reise_loeschung` (reise, von, wann, frist), `reise_vormerken`, `reise_zurueckholen`, `reise_vorgemerkt`, `faellige_loeschungen`; `loeschen` vollständig (alle Tabellen) mit Sperre letzte Organisator:in |
| engine/anmeldung.py | MODIFY | Link „Reise löschen …“, zwei Bestätigungen, Schonfrist-Block mit „Reise zurückholen“, neue Konto-Löschseite |
| engine/reisespeicher.py | MODIFY | `reisen()` ohne vorgemerkte; Ausnahme-Verbindung `_db_ausnahme`; `reise_entfernen(reise)`; `namen_ersetzen(...)`; danach `wal_checkpoint(TRUNCATE)`, `VACUUM`, `sichern()` |
| engine/konnektor.py | MODIFY | `my_trips` und alle Reise-Werkzeuge: vorgemerkte Reise wie nicht vorhanden |
| engine/schreiben.py | MODIFY | Schreibweg lehnt vorgemerkte Reise ab |
| engine/waechter.py, betrieb/waechter.sh | MODIFY | täglicher Lauf: fällige Löschungen (Speicher, Ablage, Webordner, Bauordner, Stempel), Schonfrist-Reisen überspringen; Löschprotokoll für Rückspielen alter Sicherungen |
| betrieb/veroeffentlichen.sh | MODIFY | vorgemerkte Reise nicht bauen, Webordner sofort entfernen |
| engine/texte_de.py, texte_en.py (+ weitere Sprachen) | MODIFY | `konto.seite.loeschen_*`, `konto.reise_loeschen.*`, Mails/Meldungen, `recht.datenschutz.*` (Verlauf, Belege, Sicherungen, Konto löschen) |
| docs/betrieb.md | MODIFY | Datenschutz-Tabelle, Belege nicht mehr „nie gelöscht“, Sicherungsfrist 30 Tage |
| engine/tests/test_loeschen_reise.py, test_loeschen_konto.py | CREATE | beide Beispielreisen, zwei Reisen mit gemeinsamer Ablagedatei, `pruefen()` grün danach |

### Scope Assessment
- Files: ~15 (über 7 Teilschritte, je ≤5)
- Estimated LoC: +1.700/−50 (davon ~40 % Tests)
- Risk Level: HIGH (echtes Entfernen in einem Nur-Anhängen-Speicher; ein Fehler träfe Daten anderer Reisen)

### Technical Approach
Teilschritte (Reihenfolge zwingend): **C1** ADR-0001/0009 ergänzen → **A** Vormerken und Zurückholen (konten.db, Mein Konto, beide Bestätigungen, Mails/Meldungen) → **A2** unsichtbar (Speicherliste, Konnektor, Schreibweg, Veröffentlichen entfernt Webordner, Wächter überspringt) → **A3** endgültiges Entfernen im täglichen Lauf → **B1** Konto löschen vollständig + Sperre letzte Organisator:in + Reisen nur mit der Person mit Schonfrist → **B2** Pseudonymisieren in Verlauf, Inhalten aller Versionen und Ablage-Dateien → **C2** Datenschutztext, Betrieb.

Ausnahme vom Nur-Anhängen: private Verbindung `_db_ausnahme()` ohne Authorizer; innerhalb **einer** `BEGIN IMMEDIATE`-Transaktion Trigger entfernen, Zeilen löschen bzw. umschreiben, Trigger aus `SCHEMA` neu anlegen, `COMMIT`. DDL ist in SQLite transaktional, andere Verbindungen sehen die Trigger nie fehlen; keine Schema-Migration. (Alternative: Trigger mit `WHEN fr_ausnahme()`-Funktion je Verbindung, fail-closed, braucht aber Migration; nur falls die Spec-Prüfung die Transaktionsvariante verwirft.) Quelltext-Test: genau zwei Funktionen nutzen `_db_ausnahme`. Vor jedem Löschen/Umschreiben `sichern()`, danach `pruefen()` als Abbruchkriterium.

Ablage: Datei erst nach dem Commit löschen, wenn keine Version irgendeiner Reise mehr auf die Summe verweist; Prüfen und Entfernen unter derselben Schreibsperre wie `ablage_ablegen`. Danach `wal_checkpoint(TRUNCATE)` + `VACUUM` im nächtlichen Lauf mit Timeout/Wiederholung, anschließend neuer Schnappschuss. Löschprotokoll (nur Reisekennung + Datum, konten.db) lässt den Lauf nach Rückspielen einer alten Sicherung erneut entfernen.

### Dependencies
- Upstream: SQLite (konten.db, reisen.db), Ablage, Resend, Wächter-Timer, Speicher-Umschaltung #350.
- Downstream: Seitenbau/Veröffentlichen, Konnektor, Rückmeldedienst, Sicherung, Export #498 (`konten.reise_vorgemerkt`).
- Fremd: Aufbewahrung des Server-Backups ≤30 Tage prüfen (henemm-infra, eigenes Issue in C2).

### Open Questions
- Keine offenen Produktfragen (Entscheidungen 10./11.11.2026 decken alles). Technisch entscheidet die Spec: Form des Löschprotokolls, Namen in Freitexten (nur bekannte Herkunftsmuster, im Datenschutztext ehrlich genannt).
