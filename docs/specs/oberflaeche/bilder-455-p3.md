---
entity_id: bilder-455-p3
type: feature
created: 2026-11-17
updated: 2026-11-17
status: draft
version: "1.0"
tags: [bilder, titelbild, kachel, meine-reisen, bildroute, konto, doku]
---

# Bilder Stufe 1, Paket P3: „Meine Reisen“ als Kacheln und Dokumentation (#455)

## Approval

- [ ] Approved

## Purpose

P1 (PR #585) hat Bilder als Teil der Reise angelegt, P2 (PR #592) sie auf der Reiseseite sichtbar gemacht; die Lizenzprüfung ist seit
#613 durch einen Hinweis ersetzt. P3 schließt Stufe 1 ab: „Meine Reisen“ auf Mein Konto zeigt jede Reise als Kachel mit dem Titelbild
(kleine Fassung), ausgeliefert über eine angemeldete Bildroute `/bild/<reise>/<datei>`. Ohne Titelbild steht eine ruhige Akzentfläche
mit dem App-Symbol der Reise, nie ein leerer Kasten. Dazu kommt die Doku (Route, Baustein, Ontologie, Verlauf von ADR-0001). Danach
werden #455 (Stufe 1) und #581 geschlossen. Reisen ohne Bilder (das Stadtwochenende) zeigen die Kachel mit Akzentfläche und Symbol.

## Source

- **Übergeordnete Spec (freigegeben, gilt unverändert):** `docs/specs/oberflaeche/bilder-455-stufe1.md`. P3 deckt dort V21, V22,
  AC-16 und AC-17 ab. Diese Spec wiederholt sie nicht, sondern referenziert und präzisiert sie.
- **Weitere Specs:** `docs/specs/oberflaeche/bilder-455-p2.md` (Titelbild und Daten, `daten.json` mit `bilder`),
  `docs/specs/oberflaeche/bilder-lizenzhinweis-613.md` (Lizenzprüfung entfällt, nur Hinweis; „Lizenzregel“ in V22 heißt jetzt
  Hinweis).
- **Kontext und Analyse:** `docs/context/bilder-455-p3.md` (verbindlich).
- **Files:** `engine/anmeldung.py` (`konto_seite`, Stile der Kontoseiten, `ist_unsere`, `bearbeiten`), `engine/konnektor.py`
  (`_erlaubt`), `betrieb/vorlagen/nginx-konnektor-orte.inc`, `docs/konnektor.md`, `docs/design.md`, `docs/ontologie.md`,
  `docs/adr/0001-kern.md`, Tests.
- **Kern (ADR-0001):** Das Bild bleibt Eigenschaft der Grundformen mit eigener Liste (wie die Packliste); P3 ändert keine Regel des
  Kerns.

## Dependencies

| Abhängigkeit | Art | Bedeutung |
|---|---|---|
| P2 (`bauen.bilder_daten`, `daten.json` mit `bilder`: `id`, `klein`, `titel`) | Voraussetzung | nur aktive Bilder, zurückgezogene fehlen; auf `main` |
| Stufe-1-Spec V21, V22, AC-16, AC-17 | Anforderung | Verhalten, hier präzisiert |
| Entwurf der Darstellung (Product Owner, 15.11.2026) | Anforderung | Kachel mit Titelbild, ohne Titelbild Akzentfläche mit App-Symbol |
| `konten.mitgliedschaften`, `sitzung_aus` | intern | Prüfung von Anmeldung und Mitgliedschaft |
| `instanz.seiten()`, `rm.REISE_MUSTER`, `rm.zustand` | intern | gebaute Seite je Reise, Muster der Ordnernamen, Status Archiv |
| `anmeldung.info_datei` und `/info/` | Muster | Regex auf den Dateinamen, kein Weg aus dem Ordner, 404 sonst |
| `_anmeldung_senden` (konnektor) | intern | eigene Kopfzeilen aus `kopf` gehen vor `no-store` |
| nginx-Orte (`nginx-orte-installieren.py`, #445) | Betrieb | neuer Ort wird automatisch installiert, kein Handschritt |
| Playwright (Chromium, WebKit) | Testwerkzeug | Seitentest der Kontoseite bei 360 px |
| Tests der einbindenden Instanz | Betrieb | vor dem Vorspulen mit dem Branch (neuer nginx-Ort) |

## Scope

**Gehört zu P3:** Bildroute, Kachel in „Meine Reisen“ samt Archiv, nginx-Ort, Doku (V22), Tests.

**Ausdrücklich nicht P3:** Änderungen an Reiseseite, Vorlage oder Service Worker (P2), Konnektorwerkzeuge (P1, #613), Stufe 2
(#582: eigene Fotos, echtes Löschen). Kein neues Modul, die Deploy-Liste in `betrieb/deploy.sh` bleibt unverändert.

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/anmeldung.py` | MODIFY | `ist_unsere` und `bearbeiten` um `/bild/`; neue Auflösung `bild_datei`; `konto_seite` baut Kacheln; Stil `.kachel` in den Kontostilen |
| `engine/konnektor.py` | MODIFY | `_erlaubt()` um `/bild/` (GET, HEAD, OPTIONS); Auslieferung läuft schon über `_anmeldung_senden` |
| `betrieb/vorlagen/nginx-konnektor-orte.inc` | MODIFY | `location ^~ /bild/` wie `/info/` |
| `engine/texte_<kürzel>.py` | nur falls nötig | keine neuen Texte vorgesehen (Bild dekorativ, `alt=""`); falls doch, in allen Sprachen |
| `docs/konnektor.md` | MODIFY | Route `/bild/<reise>/<datei>` |
| `docs/design.md` | MODIFY | Abschnitt Anmelde- und Kontoseiten (~Z. 237): Kachel statt Liste; Baustein `reiseKachel` |
| `docs/ontologie.md` | MODIFY | Bild als Eigenschaft der Grundformen |
| `docs/adr/0001-kern.md` | MODIFY | Verlauf: Bild als Eigenschaft; Lizenzprüfung durch Hinweis ersetzt (#613) |
| `engine/tests/test_bilder_konto.py` | CREATE | Route, Kachel, Archiv, Stadtwochenende, Bildadresse |
| `engine/tests/test_betrieb.py` | MODIFY (falls nötig) | nginx-Ort `/bild/` |
| Seitentest der Kontoseite (`engine/tests/seiten_konto.mjs` oder Playwright-Test) | MODIFY/CREATE | 360 px ohne Überbreite |

### Estimated Changes

- Files: 11 (Zeilen der Tabelle; Texte und test_betrieb.py nur falls nötig)
- LoC: +250/-15 (davon rund 120 Tests, rund 60 Doku)

## Implementation Details

### Route `GET/HEAD /bild/<reise>/<datei>` (V21, AC-16)

- `anmeldung.ist_unsere` kennt das Präfix `/bild/`, `bearbeiten` löst es auf (dort sind Sitzung und Mitgliedschaften); `konnektor._erlaubt`
  nennt `/bild/` für GET, HEAD und OPTIONS. Das Muster ist `/info/<datei>.webp` (`info_datei`).
- **Erlaubte Dateien, nur diese zwei Formen:**
  - `BI-\d+\.webp`: das Feld `klein` des aktiven Bildes mit dieser ID aus `seiten()/<reise>/daten.json` (die kleine Fassung).
  - `symbol.png`: die feste Datei `icon-192.png` der gebauten Seite (das App-Symbol, unter Friedas Adresse sonst nicht erreichbar).
- **Nie Pfade aus der Anfrage zusammensetzen.** Der Reiseordner muss `rm.REISE_MUSTER` entsprechen, der Dateiname wird nur gegen die
  feste Form geprüft und dann über `daten.json` oder den festen Namen aufgelöst. Der aufgelöste Pfad (`resolve()`) muss unter
  `seiten()/<reise>` liegen und die Datei muss existieren.
- **Eine 404-Antwort für alles Unzulässige** (gleicher Status, gleiche Kopfzeilen, gleicher Inhalt): nicht angemeldet, kein Mitglied der
  Reise, unbekannte Reise, `..` oder andere Abweichung vom Muster, große Fassung (`BI-NN-1600` o. ä.), zurückgezogenes Bild (fehlt in
  `daten.json`), fehlende Datei. So verrät die Antwort weder, ob die Reise existiert, noch ob man Mitglied ist.
- **Erfolg:** Status 200, `Content-Type: image/webp` (bzw. `image/png` für `symbol.png`), `Cache-Control: private, max-age=86400`
  statt `no-store`, `X-Content-Type-Options: nosniff`. HEAD liefert dieselben Kopfzeilen ohne Inhalt. Die CSP der Kontoseiten
  (`img-src 'self'`) passt; `_anmeldung_senden` übernimmt die eigenen Kopfzeilen aus `kopf`.
- **nginx:** `location ^~ /bild/` mit denselben Einstellungen wie `/info/` in `nginx-konnektor-orte.inc`. Der Installer akzeptiert
  Präfix-Orte mit `/` am Ende und installiert sie seit #445 selbst.

### Kachel (Baustein `reiseKachel` der Kontoseiten, V21)

- Gestaltung nach dem freigegebenen Entwurf; der Baustein gehört zu den eigenen kleinen Stilen der Kontoseiten (`anmeldung.py`),
  nicht zur Vorlage der Reiseseite.
- **Aufbau:** oben das Bild im Verhältnis 16:7 (dekorativ, `alt=""`, `loading="lazy"`), darunter Titel und Rolle wie bisher
  (`.was`, `.titel`, `rolle_marke`). Der Link geht wie heute auf `info["seite"]`. Personen-Block und „Reise löschen …“ bleiben unter der Kachel.
- **Titelbild:** das erste aktive Bild mit `titel: true` in `daten.json`; Quelle ist `/bild/<reise>/<BI>.webp`.
- **Ohne Titelbild:** Fläche in Akzentfarbe (`--acc` der Kontostile) mit dem App-Symbol mittig, `/bild/<reise>/symbol.png`. Fehlt das
  Symbol, bleibt nur die Fläche.
- **Reise ohne gebaute Seite** (`info["seite"]` fehlt): Kachel ohne Link, Fläche ohne Symbol.
- **Archiv:** weiter in `<details class="archiv">`, mit denselben Kacheln (ein Baustein statt zwei Darstellungen).
- **Vorgemerkte Reisen** (Löschvormerkung, #381) bleiben unverändert im Block oben.
- **Rahmen:** `class="liste"` bleibt als Rahmen der Kacheln erhalten (`engine/tests/test_loeschen_reise.py:290` hängt daran).
  Eine Spalte, ab 760 px Breite zwei; bei 360 px keine Überbreite.

### Präzisierung AC-16: „der geheime Link taucht nie auf“

Geheime Reiselinks gibt es seit #421 nicht mehr; der Kachel-Link auf die Reiseseite ist wie bisher für Mitglieder sichtbar. Gemeint ist
und geprüft wird: **Die Bildadresse enthält nur den Ordnernamen der Reise, nie die Adresse der Reiseseite** (`info["seite"]`), und die
Bildroute gibt nie etwas davon preis.

### Doku (V22, AC-17)

- `docs/konnektor.md`: Route `/bild/<reise>/<datei>` mit Rechten (angemeldet, Mitglied), den zwei erlaubten Formen und der einheitlichen
  404-Antwort. Die Werkzeugliste steht seit P1 dort; „Lizenzregel“ heißt seit #613 Hinweis.
- `docs/design.md`: Abschnitt Anmelde- und Kontoseiten (~Z. 237): „Deine Reisen als Liste“ wird Kachel; Baustein `reiseKachel` in der
  Bausteinliste.
- `docs/ontologie.md`: Bild als Eigenschaft der Grundformen (eigene Liste wie die Packliste, keine neue Grundform).
- `docs/adr/0001-kern.md`, Verlauf: Bild als Eigenschaft der Grundformen; Lizenzprüfung durch Hinweis ersetzt (#613).

### Prüfstelle ADR-0001

1. Ontologie statt Sonderfall: ja; Wanderung (mit Bildern) und Stadtwochenende (ohne) sind durchgespielt.
2. Kein Katalog: ja, keine Art, kein Merkmal.
3. Keine KI in Frieda: ja, reine Darstellung und Zugriffsregel im Code.
4. Die Tür: unverändert (`image_add`, `image_update`); P3 ändert den Konnektor nur um die Erlaubnisliste der Methoden.
5. Herkunft: unberührt; die Kachel zeigt kein Foto mit Nennung (dekorativ), die Nennung steht an den Bildern der Reiseseite (P2).
6. Rollen entscheiden: Mitgliedschaft entscheidet über die Auslieferung; Nicht-Mitglieder bekommen dieselbe Antwort wie bei „nicht vorhanden“.
7. IDs und Verlauf: keine neue Vergabe, kein Löschen.
8. PWA: unberührt; die Kontoseiten sind nicht Teil des Precache.
9. Claude Code: Reiseinhalte entstehen weiter im AI-Client.
10. Dokumentation: Route, Baustein, Ontologie und Verlauf (siehe oben).

## Expected Behavior

- **Mitglied, Reise mit Titelbild:** „Meine Reisen“ zeigt die Kachel mit dem Titelbild (16:7), darunter Titel und Rolle; ein Klick führt
  zur Reiseseite.
- **Mitglied, Reise ohne Titelbild** (etwa das Stadtwochenende): Akzentfläche mit App-Symbol, sonst gleich.
- **Reise ohne gebaute Seite:** Kachel ohne Link, Fläche ohne Symbol.
- **Archiv:** aufklappbar, gleiche Kacheln.
- **Bildroute:** liefert nur kleine Fassungen aktiver Bilder und das Symbol an angemeldete Mitglieder; alles andere ergibt dieselbe 404-Antwort.

## Test Plan

### Automated Tests (TDD RED)

Neue Datei `engine/tests/test_bilder_konto.py` (Beispielreise mit Bildern, Stadtwochenende ohne; erfundene Konten und Reisen). Je
Fall ein Test, zuerst der Test, dann der Code.

- [ ] GIVEN ein Mitglied der Beispielreise WHEN `GET /bild/<reise>/BI-NN.webp` mit der kleinen Fassung eines aktiven Bildes THEN 200 mit
  `Content-Type: image/webp`, `Cache-Control: private, max-age=86400`, `X-Content-Type-Options: nosniff`; HEAD ebenso ohne Inhalt.
- [ ] GIVEN ein Mitglied WHEN `GET /bild/<reise>/symbol.png` THEN 200 mit `image/png` und denselben Schutz-Kopfzeilen.
- [ ] GIVEN keine Anmeldung WHEN `GET /bild/<reise>/BI-NN.webp` THEN 404.
- [ ] GIVEN ein angemeldetes Nicht-Mitglied THEN 404 (gleicher Status, gleiche Kopfzeilen, gleicher Inhalt wie bei unbekannter Reise).
- [ ] GIVEN eine unbekannte Reise oder ein Ordnername gegen `rm.REISE_MUSTER` THEN 404.
- [ ] GIVEN `..` oder ein anderes Muster in Ordner oder Datei (auch kodiert, `%2e%2e`) THEN 404.
- [ ] GIVEN die große Fassung eines Bildes THEN 404.
- [ ] GIVEN ein zurückgezogenes Bild (fehlt in `daten.json`) THEN 404.
- [ ] GIVEN eine fehlende Datei zu einem Eintrag in `daten.json` THEN 404.
- [ ] GIVEN `POST /bild/…` THEN keine Auslieferung; `_erlaubt` nennt GET, HEAD und OPTIONS für `/bild/`.
- [ ] GIVEN ein Mitglied der Beispielreise WHEN „Meine Reisen“ gebaut wird THEN steht die Kachel mit `<img src="/bild/<reise>/BI-NN.webp">`
  (Titelbild, `alt=""`, `loading="lazy"`), Titel und Rolle darunter, Link auf die Reiseseite; der Rahmen `class="liste"` bleibt.
- [ ] GIVEN eine Reise ohne Titelbild WHEN gebaut THEN Akzentfläche mit `<img src="/bild/<reise>/symbol.png">`; ohne Symbol nur die Fläche.
- [ ] GIVEN eine Reise ohne gebaute Seite THEN Kachel ohne Link und ohne Symbol.
- [ ] GIVEN eine archivierte Reise THEN steht dieselbe Kachel in `<details class="archiv">`; vorgemerkte Reisen sind unverändert.
- [ ] GIVEN das Stadtwochenende THEN Fläche mit Symbol, keine Bildadresse auf ein Foto, keine Fehler.
- [ ] GIVEN die gebaute Kontoseite THEN enthält keine Bildadresse die Adresse der Reiseseite (`info["seite"]`), nur den Ordnernamen.
- [ ] `test_betrieb.py`: GIVEN `nginx-konnektor-orte.inc` THEN enthält sie `location ^~ /bild/`; der Installer akzeptiert den Ort.
- [ ] Seitentest Kontoseite (Chromium und WebKit): GIVEN Breite 360 px THEN keine Überbreite; GIVEN 760 px THEN zwei Spalten.
- [ ] Altbestand: `test_anmeldung.py`, `test_loeschen_reise.py`, `test_export.py`, `test_kalender.py`, `test_texte.py`, `test_design.py`
  bleiben grün; Doku-Tests (V22) prüfen die Einträge in `docs/konnektor.md` und `docs/design.md`.
- [ ] Vor dem Ausliefern laufen die Tests der einbindenden Instanz mit dem Branch (neuer nginx-Ort).

## Acceptance Criteria

Abbildung auf die Stufe-1-Spec: AC-1 bis AC-3 präzisieren AC-16, AC-4 AC-17.

- **AC-1 (AC-16, Route):** Given ein Mitglied / When `/bild/<reise>/BI-NN.webp` (kleine Fassung eines aktiven Bildes) oder `/bild/<reise>/symbol.png`
  aufgerufen wird / Then kommt 200 mit passendem `Content-Type`, `Cache-Control: private, max-age=86400` und `nosniff`; Given nicht
  angemeldet, kein Mitglied, unbekannte Reise, `..`, große Fassung, zurückgezogenes Bild oder fehlende Datei / Then kommt jeweils
  dieselbe 404-Antwort, und der Pfad wird nie aus der Anfrage zusammengesetzt.
- **AC-2 (AC-16, Kachel):** Given ein Mitglied mit Titelbild / When „Meine Reisen“ geöffnet wird / Then zeigt die Kachel das Titelbild 16:7
  über `/bild/<reise>/<BI>.webp` (dekorativ), darunter Titel und Rolle, Link auf die Reiseseite, darunter Personen und „Reise löschen“;
  ohne Titelbild die Akzentfläche mit App-Symbol, ohne gebaute Seite die Kachel ohne Link und ohne Symbol; das Archiv zeigt dieselben
  Kacheln in `<details>`; das Stadtwochenende bleibt fehlerfrei.
- **AC-3 (AC-16, Adresse und Breite):** Given die gebaute Kontoseite / When geprüft wird / Then enthält keine Bildadresse die Adresse der
  Reiseseite, und bei 360 px gibt es keine Überbreite (ab 760 px zwei Spalten).
- **AC-4 (AC-17):** Given P3 ist ausgeliefert / When die Doku geprüft wird / Then sind `docs/konnektor.md` (Route), `docs/design.md`
  (Kachel, `reiseKachel`), `docs/ontologie.md` (Bild) und der Verlauf in `docs/adr/0001-kern.md` (Bild, Hinweis statt Lizenzprüfung, #613)
  nachgeführt.

## Definition of Done

- [ ] AC-1 bis AC-4 sind erfüllt und durch Tests belegt.
- [ ] Die volle Testsuite ist ohne echte Reisen grün; der Seitentest der Kontoseite läuft in Chromium und WebKit.
- [ ] Die Tests der einbindenden Instanz laufen mit dem Branch grün (neuer nginx-Ort).
- [ ] P3 ist mit grünen Pflichtprüfungen ausgeliefert und auf dem Server der Instanz aktiv; der nginx-Ort ist ohne Handschritt installiert.
- [ ] #455 (Stufe 1) und #581 sind geschlossen.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine neue; Verlauf in ADR-0001 mit diesem Paket.
- **Rationale:** P3 stellt nur dar, was P1 als Eigenschaft der Grundformen angelegt hat, und liefert es nach Mitgliedschaft aus
  (Muster `/info/`, einheitliche 404-Antwort). Es bleibt im Rahmen von ADR-0001 (keine neue Grundform), ADR-0002 (Baustein) und
  ADR-0003 (Heimat je Grundform).

## Known Limitations

- Das Bild einer Kachel wird bis zu 24 Stunden im Browser zwischengespeichert (`private`); ein neues Titelbild erscheint danach oder
  beim erneuten Laden.
- Die Akzentfarbe ist global (`--acc` der Kontostile), nicht je Reise.
- Die Kachel zeigt keine Nennung des Bildes (dekorativ); die Nennung steht an den Bildern der Reiseseite.

## Changelog

- 2026-11-17: Erste Fassung der Paket-Spec P3 (Stufe 1 aus #455); präzisiert Stufe-1-Spec V21, V22, AC-16 und AC-17; Archiv ebenfalls
  als Kachel, Symbol-Route `symbol.png`, AC-16 auf „Bildadresse enthält nie die Adresse der Reiseseite“ präzisiert.
