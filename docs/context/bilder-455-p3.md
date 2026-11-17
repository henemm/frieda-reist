# Context: bilder-455-p3 (Bilder Stufe 1, Paket P3: „Meine Reisen“ und Doku)

## Request Summary
Letztes Paket von #455 Stufe 1: „Meine Reisen“ auf Mein Konto zeigt je Reise eine Kachel mit dem Titelbild (kleine Fassung)
über eine angemeldete Route `/bild/<reise>/<BI>.webp`, ohne Titelbild eine Akzentfläche mit dem App-Symbol der Reise; dazu die
Doku (V21, V22, AC-16, AC-17 der freigegebenen Spec `docs/specs/oberflaeche/bilder-455-stufe1.md`). P1 (#585) und P2 (#592) sind
auf main, die Lizenzprüfung ist seit #613 entfallen (nur noch Hinweis). Entwurf der Darstellung vom PO am 15.11.2026 freigegeben
(„Kachel in ‚Meine Reisen‘ ohne Titelbild mit App-Symbol“).

## Related Files
| Datei | Relevanz |
|-------|----------|
| `engine/anmeldung.py` `konto_seite()` (ab ~1062) | baut „Meine Reisen“: je Mitgliedschaft `<div class="reise">` mit Zeile (Link auf `info["seite"]`), `personen_block` (aufklappbar, darin „Reise löschen …“), Archiv in `<details class="archiv">`, vorgemerkte Reisen oben |
| `engine/anmeldung.py` Stile (~114–135) | `.liste`, `.zeile`, `.reise`; eigener kleiner Stil der Kontoseiten (Gesicht B2), nicht die Vorlage |
| `engine/anmeldung.py` `ist_unsere()` (1385), `bearbeiten()` (1391) | Routen der Anmeldeseiten; `/kalender/`, `/einladung/` als Muster für Präfix-Routen |
| `engine/konnektor.py` `do_GET` (~3575), `_marke()`, `_erlaubt()`, `_anmeldung_senden()` | Auslieferung fester Dateien und der Infobilder (`/info/<datei>.webp` über `anmeldung.info_datei`) – Muster für eine Bildroute; CSP der Kontoseiten `img-src 'self'` passt |
| `engine/konnektor.py` `daten(reise)`, `seiten()`, `symbole(reise)` | gebaute Seite unter `seiten()/<reise>/` (Ordnername): `daten.json` mit `bilder` (nur aktive, `titel`, `klein`), Dateien `medien/bilder/BI-NN-480.webp`, App-Symbol `icon-192.png` |
| `engine/bauen.py` `bilder_daten()` (~886) | schreibt aktive Bilder in `daten.json` (`id`, `klein`, `gross`, `titel`, `alt`, …); zurückgezogene fehlen dort |
| `engine/konten.py` `mitgliedschaften(konto_id)` | Prüfung der Mitgliedschaft |
| `betrieb/vorlagen/nginx-konnektor-orte.inc` | nginx-Orte zum Dienst; neue Route braucht `location ^~ /bild/`; wird seit #445 automatisch installiert (`nginx-orte-installieren.py`), kein Handschritt |
| `engine/texte_*.py` | neue sichtbare Texte (Alt-Text der Kachel, falls nötig) in allen Sprachen |
| `docs/konnektor.md` | Werkzeuge `image_add`/`image_update` schon da (P1, #613); Route `/bild/…` fehlt |
| `docs/design.md` (Abschnitt „Anmelde- und Kontoseiten“, Z. 237) | „Deine Reisen als Liste“ → Kachel beschreiben; neuer Baustein in Bausteinliste |
| `docs/ontologie.md` | Bild als Eigenschaft der Grundformen fehlt noch |
| `docs/adr/0001-kern.md` | Verlauf-Eintrag für Bilder fehlt noch |
| `engine/tests/test_anmeldung.py`, `test_bilder.py`, `test_loeschen_reise.py`, `test_export.py`, `test_kalender.py` | prüfen `konto_seite`; Struktur `class="liste"` wird in `test_loeschen_reise.py:290` erwartet |
| `engine/tests/seiten_konto.mjs`, `playwright/` | Seitentests der Kontoseite (Chromium/WebKit) |

## Existing Patterns
- Präfix-Route mit eigener Prüfung: `/kalender/<wort>.ics`, `/info/<datei>.webp` (Regex auf den Dateinamen, kein Weg aus dem Ordner).
- Nicht gefunden und nicht berechtigt antworten gleich (404), wie bei Einladungen.
- Bilddaten der Seite kommen aus `daten.json` der gebauten Seite, nicht aus dem Repo der Reise; zurückgezogene sind dort schon nicht enthalten.

## Dependencies
- Upstream: `konten` (Sitzung, Mitgliedschaften), `daten.json` und Dateien der gebauten Seite, `rm.zustand` (Status Archiv).
- Downstream: Kontoseite (alle Tests, die `konto_seite` aufrufen), nginx-Orte der Instanz, Deploy-Liste (kein neues Modul).

## Existing Specs
- `docs/specs/oberflaeche/bilder-455-stufe1.md` (V21, V22, AC-16, AC-17; freigegeben)
- `docs/specs/oberflaeche/bilder-455-p2.md`, `bilder-lizenzhinweis-613.md`

## Analyse (Summe 3, ein Durchgang)
- **Route:** `GET/HEAD /bild/<reise>/<datei>` in `anmeldung` (ist_unsere + bearbeiten) oder direkt in `konnektor.do_GET`. Erlaubte Dateien:
  `BI-\d+\.webp` (kleine Fassung des aktiven Bildes laut `daten.json`) und das App-Symbol (z. B. `symbol.png` → `icon-192.png`),
  das die Kachel ohne Titelbild braucht und unter Friedas Adresse sonst nicht erreichbar ist. Prüfung: angemeldet, Mitglied der
  Reise, Ordnername nach dem Muster der Reisenamen, Datei existiert unter `seiten()/<reise>/`; sonst 404 (gleiche Antwort).
  `Cache-Control: private, max-age=…` statt `no-store`; `X-Content-Type-Options: nosniff`.
- **Kachel:** Zeile wird zur Kachel (Bild 16:7 oben, darunter Titel und Rolle wie bisher); Link wie heute auf `info["seite"]`.
  Personen und „Reise löschen“ bleiben darunter. Archiv bleibt in `<details>` (auch dort Kacheln oder kleine Zeilen – Spec klären).
  Vorgemerkte Reisen unverändert.
- **Geheimer Link:** Die Bildadresse nutzt nur den Ordnernamen. Der Link auf die Reiseseite selbst steht schon heute als Ziel der
  Zeile auf der Kontoseite (Mitglieder dürfen ihn sehen); AC-16 „taucht nie auf“ bezieht sich auf Bildadresse und Kachelbild – in der Spec P3 präzisieren.
- **nginx:** `location ^~ /bild/` in `nginx-konnektor-orte.inc` ergänzen; der Installer erlaubt Präfix-Orte mit `/` am Ende.
- **Doku:** konnektor.md (Route), design.md (Baustein `reiseKachel` für Kontoseiten, Abschnitt Kontoseiten), ontologie.md (Bild),
  ADR-0001 Verlauf (Bild als Eigenschaft, Wegfall der Lizenzprüfung #613).

## Risks & Considerations
- Zugriffsschutz: Pfadmanipulation (`..`, fremde Reise, zurückgezogenes Bild, große Fassung) muss 404 geben; Test je Fall.
- Tests, die `class="liste"` und Zeilen von „Meine Reisen“ erwarten, dürfen nicht stillschweigend brechen.
- Reise ohne gebaute Seite (`info["seite"]` fehlt) → Kachel ohne Link, ohne Bild.
- Instanz-Tests: Meldungstexte/Schnittstelle ändern sich kaum; nginx-Ort ist neu → Tests der einbindenden Instanz vor dem Vorspulen.
- Handybreite 360 px ohne Überbreite; zwei Spalten ab 760 px.

## Analysis

### Type
Feature (letztes Paket P3 der freigegebenen Spec `docs/specs/oberflaeche/bilder-455-stufe1.md`, V21/V22, AC-16/AC-17).
Untersuchung direkt im Code statt über Hilfsagenten: Der Kontext oben war schon vollständig, geprüft wurden nur die Stellen.

### Befunde aus dem Code (17.11.2026)
- `konnektor._anmeldung()` reicht alle Anmelde-Routen an `anmeldung.bearbeiten(…, reise_kurz)`; `bearbeiten` hat die Sitzung
  (`sitzung_aus`) und gibt `(code, kopf, inhalt)` zurück. `_anmeldung_senden` setzt `Cache-Control: no-store`, eigene Kopfzeilen aus
  `kopf` gehen vor (`eigene`) → eine Bildantwort kann `Cache-Control: private, max-age=…` und `Content-Type: image/webp` selbst setzen.
  CSP `img-src 'self'` passt.
- `anmeldung` importiert schon `instanz` → `instanz.seiten() / <reise>` ist ohne neuen Parameter erreichbar; kein neues Modul (Deploy-Liste unverändert).
- `reise_kurz(reise)` → `{titel, seite}`; `seite` kommt aus `seiten.json` (die geheimen Links sind seit #421 abgeschafft, der Link ist
  die normale Adresse der Reiseseite). „Geheimer Link taucht nie auf“ (AC-16) ist damit für die Bildadresse zu prüfen: nur Ordnername.
- `daten.json` der gebauten Seite: `bilder` nur aktive, je Eintrag `id`, `klein` (`medien/bilder/BI-NN-480.webp`), `titel` (bool).
  Titelbild = erstes mit `titel: true`. Zurückgezogene fehlen → automatisch 404.
- App-Symbol der Reise: `seiten()/<reise>/icon-192.png` (oder eigenes Symbol, gleicher Dateiname). Akzentfarbe ist global
  (`PWA_FARBE` = `--acc` = `#1f7a57`), also Akzentfläche aus dem Stil der Kontoseiten, nicht je Reise.
- `/info/<datei>.webp` ist das Muster (Regex auf den Namen, Datei muss existieren, sonst 404); `_erlaubt()` nennt Präfixe für Allow.
- nginx: `location ^~ /info/ { include …konnektor.inc; }` als Vorlage für `location ^~ /bild/`.
- Tests: nur `test_loeschen_reise.py:290` hängt an `class="liste"`; Struktur `.liste` bleibt als Rahmen der Kacheln erhalten.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/anmeldung.py | MODIFY | `ist_unsere` + `/bild/`; `bild_datei(k, pfad)` (Mitglied, Ordnername nach `rm.REISE_MUSTER`, Name `BI-\d+\.webp` → `klein` laut daten.json, `symbol.png` → `icon-192.png`); Antwort mit `private`-Cache; `konto_seite` Kachel (Bild/Fläche oben, Titel+Rolle darunter), Stil `.kachel` in den Kontostilen (eine Spalte, ab 760 px zwei) |
| engine/konnektor.py | MODIFY | `_erlaubt()` um `/bild/` (GET, HEAD, OPTIONS); Bytes-Antwort läuft schon über `_anmeldung_senden` |
| engine/texte_*.py | MODIFY | ggf. Alt-Text der Kachel (Bild dekorativ → `alt=""`, dann kein Text nötig) |
| betrieb/vorlagen/nginx-konnektor-orte.inc | MODIFY | `location ^~ /bild/` mit Drossel wie Konto |
| engine/tests/test_bilder_konto.py (o. ä.) | CREATE | AC-16: Kachel mit Bild, Fläche mit Symbol, Nicht-Mitglied/fremde Reise/`..`/große Fassung/zurückgezogen → 404, nicht angemeldet → 404, Cache-Control private, kein Seitenlink in Bildadresse |
| engine/tests/test_betrieb.py | MODIFY (falls nötig) | nginx-Ort `/bild/` erwartet |
| docs/konnektor.md, docs/design.md, docs/ontologie.md, docs/adr/0001-kern.md | MODIFY | V22/AC-17 |

### Scope Assessment
- Dateien: ~8–10
- Geschätzt: +250/-15 LoC (davon ~120 Tests, ~60 Doku)
- Risk Level: MEDIUM — neue angemeldete Route mit Dateizugriff (Pfadprüfung), Kontoseite wird von vielen Tests gelesen.

### Technical Approach
Route in `anmeldung.bearbeiten` (dort sind Sitzung und Mitgliedschaften), keine Dateipfade aus der Anfrage zusammensetzen:
der Dateiname wird nur gegen eine feste Form geprüft und dann über `daten.json` (Feld `klein` des Bildes mit dieser ID)
bzw. die feste Datei `icon-192.png` aufgelöst; zusätzlich `resolve()` muss unter `seiten()/<reise>` liegen. Jede Abweichung → 404
mit gleichem Inhalt. Die Kachel nimmt das Titelbild aus `daten.json` (ohne → Akzentfläche mit `<img src="/bild/<reise>/symbol.png">`
mittig; ohne Symbol nur die Fläche). Archiv: gleiche Kacheln in `<details>`, damit es nur einen Baustein gibt. Reise ohne
gebaute Seite: Kachel ohne Link mit Fläche ohne Symbol. Bild dekorativ (`alt=""`), Titel steht darunter.
Instanz-Tests vor dem Vorspulen (neuer nginx-Ort).

### Dependencies
konten (Sitzung, `mitgliedschaften`), instanz.seiten(), daten.json der gebauten Seite, rm.zustand/REISE_MUSTER; Installer der nginx-Orte (#445).

### Open Questions
- keine Produktfrage offen (Darstellung am 15.11.2026 freigegeben). Technische Festlegung in der Spec P3: Archiv ebenfalls als Kachel; Symbol-Route `symbol.png`.
