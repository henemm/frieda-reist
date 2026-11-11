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
