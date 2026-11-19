# Context: fix-631-warteliste-push

## Request Summary
Bestätigte Einträge der Warteliste und Bitten „Reisen anlegen“ erreichen die Betreiber heute nur passiv (Claude-App `meine_reisen`, Mein Konto). Sie sollen wie andere Anfragen aufs Handy kommen (Push, Gruppe `rueckmeldungen`, Ruhezeit beachtet) und, je nach Einstellung, in die tägliche Zusammenfassung per Mail.

## Ursache
- `engine/anmeldung.py` `betreiber_melden` (Zeile ~1710) schreibt die Meldung mit `rm.meldung_anlegen(rm.ordner_neu(anlegen=True), [konto-ids], art, "reise", text, teile=…)` nach `<Konten>/neu/meldungen.jsonl`. Aufrufer: Bestätigung der Warteliste (`anfrage_warteliste`, Zeile ~1555) und Bitte „Reisen anlegen“ (`anfrage_reisen`).
- `engine/push.py` `sammeln()` läuft nur über `_reisen()` (Reiseordner der Ablage, `REISE_MUSTER`), nie über `ordner_neu()`. Die Meldungen ohne Reise werden daher nie eingereiht.

## Related Files
| File | Relevance |
|------|-----------|
| engine/push.py | `sammeln`, `sammeln_reise`, `neue`, `einreihen`, `kategorie`, `nachricht`, `titel_von`, `seite_von`, `sammeln_fuer_mail`, `zusammenfassungen` – hier kommt das Sammeln der Meldungen ohne Reise dazu |
| engine/rueckmeldungen.py | `ordner_neu`, `meldung_anlegen`, `meldungen`, `meldung_text_in`, `meldungen_des_kontos` (Quelle für Mein Konto und meine_reisen) |
| engine/anmeldung.py | `betreiber_melden`, Mein Konto (`id="meldungen"`, `id="freischalten"`) |
| betrieb/zustellen.py | legt `neue_reise` in `neu/meldungen.jsonl` an (an = Konto-Kennung, Rückfall Name) |
| engine/anmeldung.py:755 | Meldung `loeschung` in `neu/` an ein Konto |
| engine/app/sw.js | `notificationclick`: ohne url → `/konto` |
| engine/texte_*.py | `push.*` Texte; ggf. neuer Titel für Nachrichten ohne Reise |
| engine/tests/test_push.py | bestehende Tests, Fixtures `reise`, `welt` |
| docs/betrieb.md, docs/waechter.md | Abschnitte Push/Meldekanäle beschreiben, was zugestellt wird |

## Existing Patterns
- `neue(eintraege, schluessel)` merkt den Stand je Quelle in `push_stand`; erster Lauf nur merken (kein Nachschicken alter Meldungen).
- `einreihen(kid, reise, art, text, ziel, jetzt, kat)` prüft Einstellungen (Push je Gruppe, Mail täglich) und Geräte.
- `kategorie("meldung", m)`: Arten `anfrage_*`, `neue_reise`, `loeschung` fallen auf `rueckmeldungen` (Vorgabe).
- Meldungen in `neu/` adressieren Konten über die Kennung (`an` = [K-…]); `neue_reise` hat Rückfall Name, wenn keine Kennung vorhanden.
- Texte je Sprache: `rm.meldung_text_in(m, sprache)` aus `t`, sonst `m["text"]` (Sprache `VORGABE_REISE`).

## Dependencies
- Upstream: konten.db (`push_abos`, `push_einstellungen`, `push_warteschlange`, `push_stand`), `rm.ordner_neu`, `texte`.
- Downstream: `zustellen` → `nachricht(kid, reise, eintraege)`; `zusammenfassungen` (Mail). Beide kennen bisher nur Reisen.

## Risiken
- `nachricht` mit `reise=""`: `titel_von("")` ergibt leeren Titel, `seite_von("")` None → url „#reise“. Braucht Titel (Name der Instanz/Frieda aus dem Textkatalog) und Ziel Mein Konto (`<basis>/konto#freischalten` bzw. `#meldungen`).
- `sammeln_fuer_mail` prüft `_mail_an(rm.zustand(reise).regeln)`; ohne Reise gilt die Vorgabe `meldekanal` (enthält mail) – passt. `zusammenfassungen` schreibt je Reise eine Überschrift über `titel_von` – für „ohne Reise“ ebenfalls Titel nötig.
- Ältere Abos auf Reiseseiten (`sw.vorlage.js`): Klick auf ein Ziel außerhalb des Scopes öffnet ein neues Fenster – akzeptabel.
- Empfänger nur echte Konten (Kennung) – Namen als Rückfall (`neue_reise` ohne Kennung) nicht zustellbar, überspringen.
- Gesperrte Konten: `einreihen` prüft das nicht; Betreiber-Liste in `betreiber_melden` filtert schon `gesperrt = 0`.
- Erster Lauf nach dem Ausliefern: Stand nur merken, kein Schwall alter Meldungen.
- Kein Bezug zu einer echten Reise in Tests; nur erfundene Konten.

## Analysis

### Type
Bug (zugesagtes Verhalten fehlt: „Anfragen gehören zur Gruppe rueckmeldungen und kommen aufs Handy“, Kopf von `engine/push.py`).

### Ursache (bestätigt im Code)
`push.sammeln()` iteriert nur `_reisen()` (Ordner nach `REISE_MUSTER`); `rm.ordner_neu()` wird von `push.py` nie gelesen. Damit gehen alle Meldungen ohne Reise (`anfrage_warteliste`, `anfrage_reisen`, `loeschung`, `neue_reise`) weder in die Warteschlange noch in die tägliche Zusammenfassung. Lücke im Test: `test_push.py` prüft nur Meldungen in Reiseordnern.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/push.py | MODIFY | neu `sammeln_ohne_reise(jetzt)`: `neue(_jsonl(ordner_neu()/meldungen.jsonl), "meldungen:_neu")`; Empfänger = Einträge in `an`, die ein bestehendes, nicht gesperrtes Konto sind (Namen als Rückfall überspringen); Text `rm.meldung_text_in(m, sprache_von(kid)) or m["text"]`; `einreihen(kid, "", "meldung", text, ziel, jetzt, kategorie("meldung", m))`. `sammeln()` ruft es zusätzlich auf. `nachricht()`, `titel_von()`, `seite_von()` bzw. URL-Bildung: bei `reise == ""` Titel aus Textkatalog und URL `konten.basis()+"/konto#…"` (Betreiber-Anfragen `#freischalten`, sonst `#meldungen`); `neue_reise` mit Ziel-Reise → Reiseseite dieser Reise. `zusammenfassungen`: Überschrift für `reise == ""` aus dem Katalog, Link Mein Konto. `sammeln_fuer_mail` ohne Reise: Vorgabe `meldekanal` (enthält mail) – ok, aber explizit statt über `zustand("")` |
| engine/texte_de.py, engine/texte_en.py | MODIFY | neuer Schlüssel `push.titel_ohne_reise` (z. B. „Frieda“ / „Frieda“) und ggf. `push.mail.zusammenfassung.ohne_reise` („Konto und Anfragen“) |
| engine/tests/test_push.py | MODIFY | Tests: bestätigte Warteliste → Push an Betreiber mit Gerät; Bitte „Reisen anlegen“ ebenso; Ruhezeit hält zurück; Gruppe rueckmeldungen aus → kein Push; Mail täglich → in Zusammenfassung; erster Lauf nur merken; zweiter Lauf nichts doppelt; gesperrtes Konto/Name statt Kennung → nichts; Nachricht hat Titel und URL Mein Konto |
| docs/betrieb.md (Abschnitt Push) | MODIFY | „auch Meldungen ohne Reise (Anfragen an Betreiber, neue Reise, Löschung)“ |

### Scope Assessment
- Files: 5
- Estimated LoC: +60 Code / +90 Tests / +6 Texte/Doku
- Risk Level: LOW–MEDIUM (zentraler Push-Lauf; Erweiterung nur additiv, eigener Stand-Schlüssel, erster Lauf merkt nur)

### Technical Approach
Generisch statt Sonderfall: Alle Meldungen in `neu/` an Konto-Kennungen werden wie Reise-Meldungen behandelt (gleicher `neue`-Mechanismus, gleiche `kategorie`, gleiche Einstellungen/Ruhezeit). Die Warteschlange trägt `reise = ""`; `zustellen` gruppiert schon je `reise`, damit kommen Nachrichten ohne Reise gebündelt als eine eigene Nachricht mit `tag = "frieda-konto"`. Gerät: `ziele(abos, "")` nimmt das zuletzt aufgefrischte Abo je Gerät – passt. Der Service Worker öffnet ein Ziel derselben Herkunft im vorhandenen Fenster (`/konto#freischalten`), keine Änderung an `sw.js` nötig. Kein Datenformatwechsel → kein `nachziehen` nötig. Kein Deploy-Modul neu.

Bewusst mit drin: `neue_reise` (Link zur neuen Reise aufs Handy) und `loeschung` (Hinweis zur Löschung) – fallen sonst gleich durch dieselbe Lücke; Zuordnung über `kategorie` (Vorgabe `rueckmeldungen`).

### Befunde gegen den Plan
- `neue_reise` geht auch an Konten, die die Mail mit dem Link schon bekommen: doppelte Benachrichtigung möglich, aber gewünscht (Handy), und nur einmal je Eintrag.
- Mail-Text in der Meldung des Betreibers enthält die E-Mail-Adresse der Person; Push geht nur an Betreiber-Geräte (Ende-zu-Ende verschlüsselt über Web Push) – vertretbar, aber Text über `meldung_text_in` (Teile ohne Adresse? prüfen: `konto.meldungen.text.anfrage_reisen` enthält `email`).

### Dependencies
konten.db (`push_abos`, `push_einstellungen`, `push_warteschlange`, `push_stand`), `rm.ordner_neu`, `rm.meldung_text_in`, `konten.konto`, `konten.basis`, `texte`.

### Open Questions
- keine Produktfrage offen (Issue vom Owner legt Ziel fest: Push Gruppe rueckmeldungen, Ruhezeit, tägliche Zusammenfassung, einmal je Eintrag, nichts Altes).
