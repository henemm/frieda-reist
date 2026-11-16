---
entity_id: bilder-455-p2
type: feature
created: 2026-11-16
updated: 2026-11-16
status: draft
version: "1.0"
tags: [bilder, titelbild, grossansicht, offline, oberflaeche, bausteine]
---

# Bilder Stufe 1, Paket P2: Oberfläche, Großansicht, Offline (#455)

## Approval

- [ ] Approved

## Purpose

P1 (ausgeliefert, PR #585) hat Bilder als eigenen Teil der Reise angelegt (`plan/bilder.yaml`, Kennung `BI-NN`, Herkunft, Lizenz,
zwei WebP-Fassungen), zeigt sie aber nur als `![…](BI-NN)` im Text. P2 macht sie sichtbar: Titelbild, Kopfbilder an der Heimat der
Dinge, Bildreihe, Vorschaubilder, Bild im Wissenstext und eine Großansicht, alles nach dem freigegebenen Entwurf (Variante A,
Product Owner, 15.11.2026), und lädt sie offline in zwei Stufen. Reisen ohne Bilder (das Stadtwochenende) bleiben unverändert.

## Source

- **Übergeordnete Spec (freigegeben, gilt unverändert):** `docs/specs/oberflaeche/bilder-455-stufe1.md`. P2 deckt dort AC-11 bis
  AC-15 und die Verhalten V3 (`offline_mb`), V12 bis V20 und V24 (Titelbild und Kopfbilder der Beispielreise) ab. Diese Spec wiederholt
  sie nicht, sondern referenziert und präzisiert sie.
- **Kontext und Analyse:** `docs/context/bilder-455-p2.md` (verbindlich), Grundkontext `docs/context/bilder-455-stufe1.md`.
- **Files:** `engine/bauen.py`, `engine/vorlage.html`, `engine/sw.vorlage.js` (nur Kommentar), `engine/texte_<kürzel>.py` (alle
  Sprachen), `docs/design.md`, `THIRD_PARTY.md`, Beispielreise (`plan/bilder.yaml`, `medien/bilder/`), Tests.
- **Kern (ADR-0001):** Das Bild bleibt Eigenschaft der Grundformen mit eigener Liste (wie die Packliste); P2 ändert keine Regel des
  Kerns.

## Dependencies

| Abhängigkeit | Art | Bedeutung |
|---|---|---|
| P1 (`engine/bilder.py`: `laden`, `aktiv`, `gemeinfrei`, `holen`, `fassungen_schreiben`) | Voraussetzung | Datenformat, Fassungen in der Ablage, Nennungsfelder; auf `main` |
| Stufe-1-Spec V3, V12 bis V20, V24 | Anforderung | Verhalten, hier präzisiert |
| Entwurf Variante A (15.11.2026) | Anforderung | Maße, Stellen, Markup der Bausteine |
| ADR-0002, ADR-0003 | Regel | Bausteine nach Atomic Design, eine Heimat je Grundform |
| Meta-CSP `img-src 'self' data:` (P1) | intern | Großansicht und Bilder laden nur von der eigenen Seite |
| `engine/sw.vorlage.js` (`DATEIEN`, `ausSpeicher`) | intern | Precache-Liste aus dem Bau; Nicht-Vorgeladenes speichert der Worker beim Ansehen |
| Wikimedia Commons | extern | nur einmalig für neue Beispielbilder (Schritt 0, über `bilder.holen`); in Tests kein Netz |
| Playwright (Chromium, WebKit) | Testwerkzeug | Seitentests, schon im Repo in Gebrauch |
| Tests der einbindenden Instanz | Betrieb | vor dem Vorspulen mit dem Branch (Seitendaten, Texte) |

## Scope

**Gehört zu P2:** Daten an die Vorlage, Precache-Trennung, Bild im Text als Baustein, alle Bausteine und Stellen, Großansicht,
Texte in allen Sprachen, Bausteinseite und `docs/design.md`, Beispielbilder, Angleichung `--r-gross`.

**Ausdrücklich nicht P2:** P3 (Kachel in „Meine Reisen“ mit Route `/bild/<reise>/<BI>.webp`, `docs/konnektor.md`-Route,
`docs/ontologie.md`, ADR-0001-Verlauf) sowie alles aus Stufe 2 (#582: eigene Fotos, echtes Löschen). P1-Werkzeuge, Lizenzregel
und Hotlink-Sperre bleiben unverändert.

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `beispiel/reisen/beispielreise/plan/bilder.yaml`, `medien/bilder/` | MODIFY/CREATE | neue echte freie Commons-Bilder (nur CC0, CC BY, CC BY-SA): Titelbild, Kopfbilder an Ort (Gruppe mit 3 Bildern), Tag, Etappe, Unterkunft (erste Nacht) |
| `THIRD_PARTY.md` | MODIFY | je neues Bild eine Zeile: Datei, Urheber, Lizenz, Seite, als Beispielwert markiert |
| `engine/bauen.py` | MODIFY | `daten()["bilder"]`, Trennung Kopie und Precache, Offline-Warnung, Bild im Text als `figure`, Bildlink `[Text](BI-NN)` |
| `engine/vorlage.html` | MODIFY | Bausteine (Atome, Molekül, Organismus), Hilfsfunktionen, Stellen, Großansicht, Bausteinseite, Kopfkommentar |
| `engine/sw.vorlage.js` | MODIFY | nur Kopfkommentar („alle Bilder vorab“ korrigieren); Logik unverändert |
| `engine/texte_*.py` | MODIFY | neue Seitentexte und Bauwarnung in allen Sprachen |
| `docs/design.md` | MODIFY | neue Bausteine |
| `engine/tests/test_bilder.py`, `engine/tests/test_pwa.py` | MODIFY | Daten, Precache, Warnung, Stadtwochenende; P1-Tests zu AC-8 auf `figure` umstellen |
| `engine/tests/test_seite_bilder.py` | CREATE | Seitentests Chromium und WebKit |

### Estimated Changes

- Files: 12 (Tabelle mit Sammelzeilen für Texte, Tests und Beispielreise)
- LoC: +1600/-30 (überwiegend Vorlage), Tests zusätzlich

## Implementation Details

### Datenvertrag `daten()["bilder"]` (V12)

- Der Schlüssel `bilder` steht in `daten.json` nur, wenn die Reise aktive Bilder hat. Ohne aktive Bilder fehlt er ganz (anders als
  `packliste: null`), damit AC-12 „keine Bilddaten“ gilt. Die Vorlage liest immer `(D.bilder || [])`.
- Ein Eintrag je aktivem Bild: `id`, `zu`, `klein`, `gross` (Pfade unter `medien/bilder/`), `alt`, `bildunterschrift`, `titel`
  (Wahrheitswert Titelbild) und `nennung`. `nennung` ist `{urheber, lizenz, lizenz_url, seite}` oder `null` (bei `quelle: reise` und
  wenn keine Nennung nötig ist; bei gemeinfreien Bildern nur `urheber`, V16). Die Nennung steht als Daten, nicht als HTML; die
  Vorlage setzt sie als Text und Link zusammen (Urheber nie als HTML einfügen, V9).
- Zurückgezogene Bilder fehlen. Die Reihenfolge je Ding ist die der Liste; das erste Bild eines Dings ist sein Kopfbild.

### Precache-Trennung (V20, AC-14)

- Kopiert werden alle Fassungen der aktiven Bilder in die Ablage der Seite (`self.bilder`, wie heute; `pwa_schreiben` räumt weiter
  alle kopierten Dateien auf).
- Neu getrennt: `self.vorab` ist die Liste für `__DATEIEN__` des Service Workers: alle kleinen Fassungen plus die große Fassung des
  Titelbilds und je Ding des Kopfbilds. Übrige große Fassungen speichert der Worker beim Ansehen (`ausSpeicher`), dafür braucht er
  keine Logikänderung. Die JPEG-Pipeline unter `medien/` bleibt unverändert.
- Große Fassungen von Bildern im Text bleiben im Precache (V10a, wie P1).
- Summe der Vorab-Bilddateien größer als `bilder.offline_mb` aus `reise.yaml` (Standard 25): Warnung mit Katalogtext, der Bau gelingt.

### Bild im Text (V15, V10a)

- Im Bau wird `![…](BI-NN)` zu `<figure><button class="bild text" data-bild="BI-NN" aria-label="…"><img …></button><figcaption>`
  mit `.bildtext` (Bildunterschrift von Claude) und `.nennung` (von Frieda). Das ersetzt die P1-Zeile `<br><small class="nennung">`
  (`nennungen_setzen`). Der Umbau geschieht im Bau, damit Text offline und ohne JavaScript gleich aussieht.
- Neu: Bildlink im Satz `[Text](BI-NN)` wird nach V12 der Stufe-1-Spec als Bild gezeigt: Der Linktext bleibt im Satz stehen, direkt
  nach dem Absatz folgt dasselbe `figure` wie bei `![Text](BI-NN)` (der Linktext ist der Alternativtext, falls das Bild keinen hat); der Klick öffnet die Großansicht.
  Zurückgezogen: der Link wird zu reinem Text ohne Fehler; unbekannte Kennung: Baufehler wie bei `![…]`.

### Bausteine nach Entwurf Variante A (V19)

| Baustein | Ebene | Maße und Verhalten |
|---|---|---|
| `.bild` | Atom | Knopf mit `cursor: zoom-in`, Radius `var(--r)`, `img` mit `object-fit: cover` |
| `.bild.titel` | Atom | 16:10, Radius `var(--r-gross)` |
| `.bild.kopf` | Atom | 16:9 |
| `.bild.text` | Atom | Seitenverhältnis des Bildes (`auto`, `height: auto`), Spaltenbreite |
| `.nennung` | Atom | `.75rem`, Farbe `var(--mut)`, Links ebenfalls `var(--mut)` |
| `.bildtext` | Atom | `var(--t-klein)` |
| `.mini` | Atom | 44 × 44 px, Radius `var(--r-klein)` |
| `.galerie` | Molekül | Flex mit Abstand 8 px; Bilder 72 × 54 px, Radius `var(--r-klein)`; Eintrag „n Bilder“ |
| `#gross` | Organismus | Großansicht (siehe unten) |

Alle Maße als Tokens der Vorlage; `--r-gross` (18 px), `--r-klein` und `--r` sind dort vorhanden. Die Stufe-1-Spec nennt in V13
`--radius-gross`; dieser Token existiert nicht, gemeint ist `--r-gross`. Mit dieser Spec ist V13 entsprechend angeglichen, der
16-px-Rückfall entfällt. Markup je Bild: `<figure><button class="bild …" aria-label="Großansicht: …"><img alt></button><figcaption
class="nennung">`. Jeder Baustein steht im Kopfkommentar, in den Stilen seiner Ebene, auf der Bausteinseite und in
`docs/design.md`; `GRUNDFORMEN` nur, falls ein Baustein eine Grundform zeigt (Heimat je ADR-0003). Hilfsfunktionen: `bilderZu(id)`,
`bildEl`, `miniEl`, `galerieEl`, `kopfBild`.

### Stellen (V13, V14)

- **Titelbild:** ganz oben in `ansichtReise`, vor `.reisekopf`, 16:10, darunter klein die Nennung, darunter der Reisekopf wie heute.
- **Tagesliste (`tagZeile`):** rechts ein Mini (44 px) bei Tagen mit Kopfbild; Tage ohne Bild unverändert, das `tz-*`-Grid bleibt ohne
  Überbreite.
- **Tag (`ansichtTag`):** Kopfbild 16:9 über der großen Tageszahl.
- **Ort (`ansichtOrt`):** Kopfbild über dem Namen, weitere Bilder desselben Dings als Bildreihe (72 × 54) mit „n Bilder“.
- **Etappe (`ansichtAbschnitt`):** Kopfbild über den Kennzahlen.
- **Unterkunft:** Kopfbild oben in der Karte (`dingKarte`) an der Heimat, der ersten Nacht (`aufenthaltBeginn`); an allen anderen
  Nächten (`nachtZeile`) nur eine Zeile mit Mini und Verweis auf die Heimat.
- Nicht-Heimat-Stellen zeigen nie ein Kopfbild (eine Heimat je Grundform).

### Großansicht (V17)

- Modales `<dialog id="gross">`, geöffnet mit `showModal()` (Fokusfalle und Escape durch den Browser). Hintergrund `rgba(8,10,9,.94)`,
  drei Zeilen: oben Zähler „Ding · i / n“ und „Schließen“, Mitte Pfeile und Bild (`object-fit: contain`), unten Bildunterschrift und
  volle Nennung. Abstände mit `safe-area-inset`.
- Gruppe = Bilder desselben Dings (`zu`); Zähler zählt in der Gruppe. Das Bild öffnet mit der großen Fassung.
- Tastatur: Pfeil links und rechts wechseln, Escape schließt. Nach dem Schließen geht der Fokus selbst per `opener.focus()` an den
  Auslöser zurück (WebKit gibt ihn nicht verlässlich zurück).
- Wischen per Pointer-Events: waagerecht wechselt, nach unten schließt (`touch-action: pan-y`). Bis 560 px Breite sind die Pfeile
  ausgeblendet (`@media (max-width: 560px)`).
- Das Element wird erst beim ersten Öffnen erzeugt, damit Reisen ohne Bilder kein Element dafür tragen (AC-12).
- Klick per Delegation auf `[data-bild]`, keine Inline-Handler (CSP). Die Großansicht lädt nichts Fremdes.

### Texte (V19)

Neue Seitentexte in `engine/texte_<kürzel>.py` aller Sprachen: „n Bilder“, „Schließen“, „Großansicht: …“, „vorheriges Bild“,
„nächstes Bild“, Zähler, Rahmen der Bildunterschrift, dazu die Bauwarnung zur Offline-Grenze. Die Ausnahmelisten in
`engine/tests/test_texte.py` werden nicht länger.

### Beispielbilder (V24)

Wenige neue echte freie Commons-Bilder (über `bilder.holen` und `fassungen_schreiben` aus P1, keine Wiederverwendung vorhandener
Dateien unter neuen IDs): Titelbild, Kopfbilder an Ort (Gruppe mit 3 Bildern), Tag, Etappe und Unterkunft (erste Nacht). Nur CC0,
CC BY und CC BY-SA; je Bild eine Zeile in `THIRD_PARTY.md` mit Urheber, Lizenz und Seite. Das Stadtwochenende bekommt keine Bilder.

### Prüfstelle ADR-0001

1. Ontologie statt Sonderfall: ja, Bild ist Eigenschaft der Grundformen; mit Wanderung und Stadtwochenende durchgespielt (V18).
2. Kein Katalog: ja, keine Art, kein Merkmal.
3. Keine KI in Frieda: ja, Darstellung und Regeln im Code.
4. Die Tür: gedeckt durch P1 (`image_add`, `image_update`, Eintrag in `docs/konnektor.md`); P2 ändert den Konnektor nicht.
5. Herkunft: Nennung aus P1-Feldern, Anzeige nach V16.
6. Rollen entscheiden: unberührt (Rechte aus P1).
7. IDs und Verlauf: keine neue Vergabe, kein Löschen.
8. PWA: Offline in zwei Stufen (V20), Browser-Rundgang als Seitentest.
9. Claude Code: Reiseinhalte entstehen weiter im AI-Client.
10. Dokumentation: `docs/design.md`, Bausteinseite; Verlauf in ADR-0001 folgt mit P3.

## Test Plan

### Automated Tests (TDD RED)

Je Schritt zuerst der Test, dann der Code.

- [ ] `test_bilder.py`: GIVEN Beispielreise WHEN `daten()` THEN `bilder` enthält nur aktive Bilder mit `klein`, `gross`, `alt`,
  `titel` und `nennung` als Daten (kein HTML); GIVEN ein zurückgezogenes Bild THEN fehlt es.
- [ ] `test_bilder.py`: GIVEN das Stadtwochenende WHEN gebaut THEN fehlt der Schlüssel `bilder` in `daten.json`, und die Seite
  enthält weder Bild-Elemente noch Bilddateien.
- [ ] `test_bilder.py`: GIVEN `![…](BI-NN)` WHEN gebaut THEN steht ein `figure` mit `button.bild.text[data-bild]`, `figcaption`
  und Nennung (Urheber, Lizenz-Link, Commons-Seite; gemeinfrei nur Urheber; `quelle: reise` keine Nennung); GIVEN `[Text](BI-NN)`
  THEN wird es ebenfalls als `figure` mit `button.bild.text[data-bild]` gezeigt (kein bloßer Link); GIVEN zurückgezogen THEN reiner Text; GIVEN unbekannte Kennung THEN Baufehler.
- [ ] `test_pwa.py`: GIVEN aktive Bilder THEN `__DATEIEN__` enthält alle kleinen Fassungen und die großen von Titel- und
  Kopfbildern, aber keine übrigen großen; die JPEG-Pipeline unter `medien/` ist unverändert; alle kopierten Dateien werden
  aufgeräumt.
- [ ] `test_pwa.py` / `test_bilder.py`: GIVEN Vorab-Dateien über `offline_mb` (Test mit kleinem Wert) THEN Warnung mit Katalogtext
  und der Bau gelingt.
- [ ] `test_bilder.py` (AC-8): GIVEN die Beispielreise THEN hat jedes Bild eine Lizenz aus CC0, CC BY oder CC BY-SA (bzw.
  gemeinfrei) und genau eine Zeile in `THIRD_PARTY.md` (Datei, Urheber, Lizenz, Seite); es gibt ein Titelbild und mindestens
  einen Ort mit 3 Bildern.
- [ ] `test_texte.py`, `test_design.py`: neue Schlüssel in allen Sprachen, Bausteine in Kopfkommentar, Bausteinseite und
  `docs/design.md`.
- [ ] `test_seite_bilder.py` (Playwright, Chromium und WebKit, Beispielreise): GIVEN die Startseite THEN Titelbild 16:10 mit
  Nennung vor dem Reisekopf; Mini in der Tagesliste nur bei Tagen mit Kopfbild; Kopfbild 16:9 an Ort, Etappe, Tag und Unterkunft
  (erste Nacht); Bildreihe mit „n Bilder“; Mini mit Verweis an der Nacht ohne Heimat; Bild im Wissenstext mit Unterschrift und
  Nennung.
- [ ] `test_seite_bilder.py`: GIVEN ein Kopfbild WHEN Klick THEN öffnet `#gross` mit „Ding · 1 / 3“; Pfeiltasten wechseln, Escape
  schließt und der Fokus liegt wieder auf dem Auslöser; Wischen waagerecht wechselt, Wischen nach unten schließt; bei 360 px
  sind die Pfeile ausgeblendet; vor dem ersten Öffnen gibt es kein `#gross`.
- [ ] `test_seite_bilder.py`: GIVEN Breite 360 px THEN keine Überbreite (Tagesliste, Galerie, Karten); GIVEN die Karte THEN lädt sie
  ohne CSP-Fehler in der Konsole (Seitentest aus P1 bleibt grün).
- [ ] `test_seite_bilder.py`: GIVEN das Stadtwochenende THEN keine Bild-Elemente, kein `#gross`, keine `.bild`/`.mini`/`.galerie`.
- [ ] Altbestand-Tests (`test_bauen.py`, `test_pwa.py`) und die Tests der einbindenden Instanz sind mit dem Branch grün; bekannte
  wackelige Browsertests (#565, #568) werden nicht mit neuen Fehlern verwechselt.

### Schrittfolge (je Schritt höchstens 250 Produktivzeilen, Test zuerst)

0. Beispielbilder: Daten und `THIRD_PARTY.md`, eigener Commit.
1. Bau: `bilder` in `daten()`, `self.vorab`, Offline-Warnung, Text dazu.
2. Bild im Text als `figure` und Bildlink; P1-Tests anpassen.
3. Atome und Hilfsfunktionen in der Vorlage.
4. Titelbild und Mini in der Tagesliste.
5. Kopfbild Ort mit Bildreihe, Tag, Etappe, Unterkunft (Heimat und `nachtZeile`).
6. Großansicht: (a) Dialog, Zähler, Schließen, Tastatur, Fokusrückgabe; (b) Wischen, nach unten schließen, Pfeile bis 560 px aus.
7. Bausteinseite, `GRUNDFORMEN` falls nötig, `docs/design.md`, restliche Texte.
8. Seitentests vollständig, Kommentar in `sw.vorlage.js`.

## Acceptance Criteria

Abbildung auf die Stufe-1-Spec: AC-1 und AC-2 präzisieren AC-11, AC-3 AC-12, AC-4 AC-13, AC-5 und AC-6 AC-14,
AC-7 AC-15.

- **AC-1 (AC-11):** Given die Beispielreise / When die Seite in Chromium und WebKit geöffnet wird / Then steht das Titelbild
  (16:10, Radius `--r-gross`) mit Nennung vor dem Reisekopf, die Tagesliste zeigt ein Mini (44 px) nur bei Tagen mit Kopfbild, und
  Ort, Etappe, Tag und Unterkunft an der ersten Nacht zeigen das Kopfbild (16:9) mit Bildreihe (72 × 54, „n Bilder“); an anderen
  Nächten steht nur ein Mini mit Verweis.
- **AC-2 (AC-11):** Given ein Bild im Wissenstext, ein Bildlink im Satz und die Breite 360 px / When die Seite geöffnet und
  ein Bild angeklickt wird / Then erscheinen beide als Bild mit Unterschrift und Nennung nach V16 ohne Überbreite, und die Großansicht öffnet
  mit „Ding · i / n“, Pfeil- und Escape-Taste, Fokusrückgabe, Wischen (waagerecht wechselt, nach unten schließt); bis 560 px
  sind die Pfeile ausgeblendet.
- **AC-3 (AC-12):** Given das Stadtwochenende / When gebaut und geöffnet wird / Then fehlt `bilder` in `daten.json`, es gibt
  keine Bild-Elemente, keine Bilddateien und kein `#gross`, und die Seite entspricht dem Stand vor P2.
- **AC-4 (AC-13):** Given die neuen Bausteine / When die Karte in Chromium und WebKit geöffnet wird / Then lädt sie ohne
  CSP-Fehler, und die Großansicht lädt nur von der eigenen Seite (keine Inline-Handler).
- **AC-5 (AC-14):** Given aktive Bilder / When gebaut wird / Then enthält `__DATEIEN__` alle kleinen Fassungen und die großen
  von Titel- und Kopfbildern, übrige große nicht, und die JPEG-Pipeline unter `medien/` verhält sich wie vorher.
- **AC-6 (AC-14):** Given die Summe der Vorab-Bilddateien liegt über `bilder.offline_mb` / When gebaut wird / Then gibt es eine
  Warnung mit Katalogtext, und der Bau gelingt.
- **AC-7 (AC-15):** Given die neuen Bausteine und Texte / When die Prüfungen laufen / Then stehen sie in Kopfkommentar,
  Bausteinseite, `docs/design.md` und allen Sprachdateien, und die Ausnahmelisten in `test_texte.py` sind nicht länger.
- **AC-8 (V24):** Given die Beispielreise / When ihre Bilder geprüft werden / Then sind es echte freie Bilder (CC0, CC BY oder
  CC BY-SA) mit je einer Zeile in `THIRD_PARTY.md`, mit Titelbild und einer Gruppe von 3 Bildern an einem Ort.

## Definition of Done

- [ ] AC-1 bis AC-8 sind erfüllt und durch Tests belegt.
- [ ] Die volle Testsuite ist ohne echte Reisen grün; die Seitentests laufen in Chromium und WebKit.
- [ ] Die Tests der einbindenden Instanz laufen mit dem Branch grün (Seitendaten, Texte).
- [ ] P2 ist mit grünen Pflichtprüfungen ausgeliefert und auf dem Server der Instanz aktiv; vorhandene Reisen veröffentlichen ohne Fehler.
- [ ] Bausteinseite und `docs/design.md` sind nachgeführt; #455 bleibt bis nach P3 offen.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine neue; Verlauf in ADR-0001 folgt mit P3.
- **Rationale:** P2 stellt nur dar, was P1 als Eigenschaft der Grundformen angelegt hat (Muster der Packliste), folgt ADR-0002
  (Bausteine) und ADR-0003 (eine Heimat je Grundform) und berührt die Prüfstelle von ADR-0001 nicht negativ (siehe oben).

## Known Limitations

- Nach einer neuen Version des Service Workers sind nur beim Ansehen geladene große Fassungen wieder weg und werden beim nächsten
  Ansehen erneut geladen (gemeint ist „beim Ansehen“ nach V20).
- Die Offline-Grenze ist nur eine Warnung; der Bau bricht bei Überschreitung nicht ab (V3).

## Changelog

- 2026-11-16: Erste Fassung der Paket-Spec P2 (Stufe 1 aus #455); präzisiert Stufe-1-Spec V12 bis V20, gleicht den Token auf
  `--r-gross` an.
- 2026-11-16: Bildlink im Satz wird nach V12 als Bild gezeigt (nicht nur als Link); Test für die Beispielbilder (AC-8) ergänzt;
  Kriterien als AC-1 bis AC-8 nummeriert.
