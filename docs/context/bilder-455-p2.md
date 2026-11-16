# Context: bilder-455-p2

## Request Summary
Paket P2 der freigegebenen Spec `docs/specs/oberflaeche/bilder-455-stufe1.md` (#455): Bau übergibt aktive Bilder an die Vorlage,
alle Bausteine nach dem freigegebenen Entwurf (Variante A, PO 15.11.2026), Service Worker zweistufig offline. Kriterien AC-11 bis
AC-15, Verhalten V3 (offline_mb), V12–V20, V24 (Titelbild/Kopfbilder der Beispielreise). P1 ist mit PR #585 auf `main`; P3
(Meine Reisen, Doku) folgt danach. Grundkontext bleibt `docs/context/bilder-455-stufe1.md` (verbindlich, nicht wiederholt).

## Entwurf (freigegeben) – Quelle der Maße
Privates Artefakt `https://claude.ai/artifact/3FirFRujJz9jyTirqAFr1p` (Variante A). Entwurf-CSS (Tokens wie Vorlage):
- `.bild` (Knopf, `cursor:zoom-in`, `border-radius:var(--r)`), `.bild img{object-fit:cover}`; `.bild.titel{aspect-ratio:16/10;border-radius:var(--r-gross)}`,
  `.bild.kopf{aspect-ratio:16/9}`, `.bild.text{aspect-ratio:auto}` (img `height:auto`).
- `.nennung{font-size:.75rem;color:var(--mut)}` (Links ebenfalls `--mut`), `.bildtext{font-size:var(--t-klein)}`.
- `.galerie{display:flex;gap:8px}`, `.galerie .bild{width:72px;height:54px;border-radius:var(--r-klein)}`, `.galerie .mehr` „n Bilder“.
- `.mini{width:44px;height:44px;border-radius:var(--r-klein)}` (Tagesliste rechts, Zeilen an Nicht-Heimat-Stellen).
- `#gross` fester Dialog `rgba(8,10,9,.94)`, Zeilen oben (Zähler „Ding · 1 / 3“ + „Schließen ✕“) / Mitte (Pfeile ‹ › + Bild
  `object-fit:contain`) / unten (Bildunterschrift + volle Nennung); `@media (max-width:560px){#gross .pfeil{display:none}}`;
  `touch-action:pan-y`; safe-area-Abstände. Markup je Bild: `<figure><button class="bild …" aria-label="Großansicht: …"><img alt></button><figcaption class="nennung">`.
- Prüfen: ob `--r-gross`, `--r-klein`, `--r` in der Vorlage existieren (Spec V13: sonst 16 px).

## Related Files
| File | Relevance |
|------|-----------|
| `engine/bilder.py` (P1) | `laden`, `aktiv`, `gemeinfrei`, `ORDNER` (`medien/bilder`), Felder `zu`, `titelbild`, `dateien.klein/gross`, `bildunterschrift`, `alt`, `urheber`, `lizenz`, `lizenz_url`, `seite`, `quelle` |
| `engine/bauen.py:344–347,457–526` | `self.bilder` (Quelle→Ziel, Kopie + Offline-Liste), `self.fassungen`, `bild_eintraege`, `bild_kennung` (BI im Text → große Fassung), `nennung` (V16, HTML), `bilder_umschreiben` |
| `engine/bauen.py:666 daten()` (`:824 packliste`) | Daten an die Vorlage: hier `bilder` (aktiv, je Ding gruppiert, Nennung als Daten, nicht HTML) ergänzen |
| `engine/bauen.py:1427 bilder_schreiben`, `:1499–1522 pwa_schreiben` | Kopie der Fassungen (WebP nur kopieren, `self.fassungen`); `DATEIEN` = Precache-Liste; V20: klein alle + groß Titel/Kopf; Warnung bei Summe > `offline_mb` |
| `engine/bauen.py:151` | Meta-CSP `img-src 'self' data:` (P1); Großansicht darf nichts Fremdes laden |
| `engine/sw.vorlage.js` | `DATEIEN` vorab; `ausSpeicher` speichert Ungeladenes beim Ansehen schon → V20 braucht im Worker voraussichtlich keine Logikänderung, nur die Liste aus dem Bau. Bei neuer Version gehen nur beim Ansehen geladene große Fassungen verloren (akzeptabel: „beim Ansehen“) |
| `engine/vorlage.html:1300` | `D` = daten.json, `BAUSTEINE`; Kopfkommentar Bausteine `:1405–1407` (Atome/Moleküle/Organismen) – neue Bausteine dort eintragen |
| `engine/vorlage.html:140/219/503` | CSS-Ebenen Atome/Moleküle/Organismen; `.reisekopf` `:712` |
| `engine/vorlage.html:3509 tagZeile` | Tagesliste: rechts Mini-Vorschau (44 px) bei Tagen mit Kopfbild (V13) |
| `engine/vorlage.html:3702 ansichtReise` | Titelbild 16:10 ganz oben vor `.reisekopf` (`:3709`), darunter Nennung |
| `engine/vorlage.html:4085 nachtAbschnitt` / `dingKarte` | Unterkunft: Kopfbild oben in der Karte an der ersten Nacht (Heimat); sonst `nachtZeile` mit Mini-Vorschau |
| `engine/vorlage.html:4125 ansichtTag` (`tagKopf` `:4145`) | Kopfbild über der großen Tageszahl |
| `engine/vorlage.html:4189 ansichtOrt` (`h2` `:4194`) | Kopfbild über dem Namen + Galerie |
| `engine/vorlage.html:4461 ansichtAbschnitt` | Etappe: Kopfbild über den Kennzahlen |
| `engine/vorlage.html:4317 ansichtWissen` / `leseAbschnitt` | Bild im Text: kommt als HTML aus dem Bau (`bild_kennung` + `nennung`); P2: `figure`/`bildtext` + Klick → Großansicht |
| `engine/vorlage.html:4542 GRUNDFORMEN`, `:4591 ansichtBausteine`, `:6129 heimat()` | Bausteinseite, Heimat je ID (ADR-0003) |
| `engine/texte_*.py`, `engine/tests/test_texte.py` | neue Seitentexte (n Bilder, Schließen, Großansicht, vorheriges/nächstes Bild, Zähler) in allen Sprachen |
| `docs/design.md`, `engine/tests/test_design.py` | Bausteine dokumentieren (Prüfung Kopfkommentar ↔ Bausteinseite ↔ design.md) |
| `engine/tests/test_pwa.py`, `test_bauen.py`, Seitentests (Playwright, Chromium + WebKit) | AC-11–AC-14 |
| `beispiel/reisen/beispielreise/plan/bilder.yaml`, `medien/bilder/` | Beispielbilder aus P1; für P2 Titelbild + Kopfbilder an Ort/Etappe/Tag/Unterkunft und eine Gruppe mit ≥2 Bildern nötig (ggf. ergänzen, Lizenz in `THIRD_PARTY.md`) |
| `beispiel/reisen/stadtwochenende/` | ohne Bilder, muss exakt unverändert bleiben (AC-12) |

## Existing Patterns
- Daten an die Vorlage über `daten()` → `daten.json`/`D`; Packliste ist das jüngste Muster einer eigenen Liste mit Bausteinen.
- Bausteine: Funktion `el(...)`, Eintrag im Kopfkommentar, Stile in ihrer Ebene, Abschnitt auf `#bausteine`, `docs/design.md`.
- Heimat: `heimat(id)`; Unterkunft vollständig an der ersten Nacht (`aufenthaltBeginn`), sonst `nachtZeile` mit Link.
- Bild im Text: Bau erzeugt `<img src="medien/bilder/…">` + Nennung (P1, V10a); P2 ersetzt die Nennungszeile durch den Baustein (V15).
- Offline: `DATEIEN`/`STAND` aus `pwa_schreiben`; Worker speichert Nicht-Vorgeladenes beim Abruf.

## Dependencies
- Upstream: P1-Datenformat (`plan/bilder.yaml`, Fassungen in der Ablage), Pillow nicht nötig im Bau (nur Kopie).
- Downstream: P3 (Kachel nutzt Titelbild-Kennung), Instanz-Tests (Seitendaten, Texte) vor dem Vorspulen.

## Existing Specs
- `docs/specs/oberflaeche/bilder-455-stufe1.md` (freigegeben; P2-Teil gilt unverändert)
- `docs/specs/oberflaeche/packliste-431.md` (Muster Bausteine/Liste)

## Risks & Considerations
- Größter Teil ist die Vorlage (+1500–2000 Zeilen): LoC-Grenze des Edit-Gates (250 Produktiv je Schritt) → in Schritte schneiden.
- AC-12: Stadtwochenende ohne jedes Bild-Element und ohne Bilddaten (`bilder` leer/fehlend in `daten.json`), Seitentest vergleicht.
- Großansicht: Tastatur (Pfeile, Escape), Fokusfalle und -rückgabe, Wischen (Pointer-Events), Wischen nach unten schließt; am Handy Pfeile aus.
- CSP: Großansicht und Bilder nur `'self'`; Seitentest Karte aus P1 muss grün bleiben (AC-13).
- 360 px ohne Überbreite (Galerie, Mini in Tageszeile, `tz-*`-Grid).
- Bild im Text: Nennung aus P1 ist HTML im Text; Umbau zu `figure` im Bau (`nennung`) statt in der Vorlage, damit offline/ohne JS gleich.
- Offline-Grenze: Summe der Precache-Bilddateien gegen `reise.yaml` `bilder.offline_mb` (Default 25), nur Warnung.
- Wackelige Browsertests (#565, #568) nicht mit neuen Fehlern verwechseln.

## Analysis

### Type
Feature (Paket P2 der freigegebenen Spec, keine neue Produktentscheidung)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `beispiel/reisen/beispielreise/plan/bilder.yaml`, `medien/bilder/` | MODIFY/CREATE | Schritt 0: neue echte freie Commons-Bilder (über `bilder.holen`/`fassungen_schreiben` aus P1) als Kopfbilder an Ort (Gruppe mit 3 Bildern für „Ding · 1 / 3“ und Bildreihe), Tag, Unterkunft (erste Nacht), Etappe; nur CC0/CC BY/CC BY-SA |
| `THIRD_PARTY.md` | MODIFY | je neues Bild eine Zeile (Datei, Urheber, Lizenz, Seite) |
| `engine/bauen.py` | MODIFY (~+120) | `daten()["bilder"]` nur bei aktiven Bildern (Schlüssel fehlt sonst, AC-12); Eintrag `{id, zu, klein, gross, alt, bildunterschrift, titel, nennung:{urheber, lizenz, lizenz_url, seite}|null}` als Daten, nicht HTML; alle Fassungen kopieren (`self.bilder`), Precache getrennt (`self.vorab`: alle kleinen + große von Titel/Kopfbild = erstes Bild je Ding); Warnung bei Summe > `bilder.offline_mb`; Bild im Text als `<figure>` mit `<button class="bild text" data-bild>` + `figcaption.bildtext` + `.nennung` (ersetzt `<br><small class="nennung">`/`nennungen_setzen`); Bildlink im Satz `[Text](BI-NN)` → Link mit `data-bild` (öffnet Großansicht) |
| `engine/vorlage.html` | MODIFY (~+1200–1500) | Atome `.bild`, `.nennung`, `.mini`; Molekül `.galerie`; Organismus Großansicht; `bilderZu(id)`, `bildEl`, `miniEl`, `galerieEl`, `kopfBild`, Großansicht; Stellen `ansichtReise`, `tagZeile`, `ansichtTag`, `ansichtOrt`, `ansichtAbschnitt`, `dingKarte`/`nachtZeile`; Bausteinseite, Kopfkommentar, `GRUNDFORMEN` falls nötig; Lesen immer `(D.bilder || [])` |
| `engine/sw.vorlage.js` | MODIFY (nur Kommentar) | Logik bleibt: Nicht-Vorgeladenes speichert `ausSpeicher` beim Ansehen; Kopfkommentar „alle Bilder vorab“ korrigieren |
| `engine/texte_*.py` | MODIFY | Seitentexte (n Bilder, Schließen, Großansicht, vorheriges/nächstes Bild, Zähler), Bauwarnung Offline-Grenze, Bildunterschrift-Rahmen; Ausnahmelisten nicht länger |
| `docs/design.md` | MODIFY | neue Bausteine (V19) |
| `engine/tests/test_bilder.py`, `test_pwa.py` | MODIFY | Daten an die Vorlage, Precache-Auswahl, Warnung > 25 MB, Stadtwochenende ohne `bilder`; AC-8-Tests aus P1 auf `figure` umstellen |
| `engine/tests/test_seite_bilder.py` | CREATE | Playwright Chromium + WebKit, 360 px, CSP, Großansicht, Stadtwochenende |

### Scope Assessment
- Files: ~12
- Estimated LoC: +1600/-30 (überwiegend Vorlage), Tests zusätzlich
- Risk Level: MEDIUM (große Oberflächenänderung, aber additiv; Reisen ohne Bilder bleiben unberührt)

### Technical Approach
Schnitt in Schritte ≤250 Produktivzeilen, je Schritt Test zuerst:
0. Beispielbilder ergänzen (Daten + `THIRD_PARTY.md`, eigener Commit).
1. Bau/Daten: `bilder` in `daten()`, Trennung Kopie/Precache (`self.vorab`), Offline-Warnung. Die JPEG-Pipeline unter `medien/` bleibt unverändert (kritischster Punkt: `self.bilder` heißt heute „kopieren“ und „vorab“ zugleich; Aufräumen in `pwa_schreiben` bleibt auf allen kopierten Dateien).
2. Bild im Text als `figure` im Bau (+ Bildlink im Satz), P1-Tests anpassen.
3. Atome/Hilfsfunktionen in der Vorlage.
4. Titelbild + Mini in der Tagesliste.
5. Kopfbild Ort (+ Bildreihe), Tag, Etappe, Unterkunft (Heimat erste Nacht, sonst `nachtZeile` mit Mini).
6. Großansicht: (a) modales `<dialog>` per `showModal()` (Fokusfalle, Escape vom Browser), Zähler „Ding · i / n“, Schließen, Tastatur, Fokusrückgabe zusätzlich selbst per `opener.focus()` (WebKit); (b) Pointer-Wischen, nach unten schließen, Pfeile ≤560 px aus. Dialog wird erst beim ersten Öffnen erzeugt (AC-12: kein Element bei Reisen ohne Bilder). Klick per Delegation auf `[data-bild]`, keine Inline-Handler (CSP).
7. Bausteinseite, `GRUNDFORMEN`, `docs/design.md`, restliche Texte.
8. Seitentests komplett + SW-Kommentar.

### Entscheidungen (Tech Lead)
- `bilder` fehlt in `daten.json`, wenn keine aktiven Bilder (anders als `packliste: null`), weil AC-12 „keine Bilddaten“ verlangt; kein bestehender Test vergleicht `daten.json` des Stadtwochenendes.
- Neue echte Commons-Bilder statt Wiederverwendung vorhandener Dateien unter neuen IDs (V24 „echte freie Bilder“, glaubwürdige Gruppe, ehrliche Offline-Summe).
- Bildlink im Satz (V12) = `[Text](BI-NN)`: heute ohne Code (`BILD_KENNUNG_IM_TEXT` erfasst nur `![…]`); wird in Schritt 2 mitgebaut, Ziel ist die große Fassung, Klick öffnet die Großansicht.
- Spec V13 nennt `--radius-gross`; in der Vorlage heißt der Token `--r-gross` (18 px, vorhanden) → in der Spec-Ergänzung von P2 angleichen.

### Dependencies
- Upstream: P1 (`engine/bilder.py`: `laden`, `aktiv`, `gemeinfrei`, `holen`, `fassungen_schreiben`; `bild_kennung`, `nennung_html`).
- Downstream: P3 (Kachel „Meine Reisen“ nutzt das Titelbild aus `bilder`), Instanz-Tests vor dem Vorspulen (Seitendaten, Texte).

### Open Questions
- keine Produktfrage offen (Entwurf Variante A freigegeben 15.11.2026; Spec freigegeben).
