# Kontext: feat-711-galerie (Issue #711, Etappe 1)

## Auftrag
Freigegebener Entwurf (Product Owner, 26.11.2026): Galerie auf der Infoseite (wischbare Reihe, PhotoSwipe mit Unterschrift im
eigenen dunklen Streifen), Karte „Was Frieda alles kann“ statt des GitHub-Links, Seite „Alle Funktionen“ unter /info/,
Muster-Unterseite „Reiseseite“; Deutsch und Englisch.

## Betroffene Dateien
- `engine/anmeldung.py`: Infoseite (`info_seite`, `INFO_BILDER`, `info_datei`), Stil `CSS`, Routen in `bearbeiten` (`/`, `/info/`), `ist_unsere`.
- `engine/konnektor.py`: `do_GET` liefert alles unter `/info/…` außer `/info/` als Bild (`info_datei`) oder 404; `_marke` (Cache-Kopf).
- `engine/texte_de.py`, `engine/texte_en.py`: Schlüssel `info.…`; die Pseudo-Sprache `engine/tests/texte_xx.py` leitet sich von Englisch ab.
- `engine/app/` (rsync nach `<FR_DIENST>/app/`), `engine/vendor/photoswipe-5.4.4.*` (rsync nach `<FR_DIENST>/vendor/`).
- `engine/info/erzeugen.py`, `engine/info/aufnehmen.mjs`: Bilder je Sprache aus den Beispielreisen.
- Tests: `engine/tests/test_infoseite.py` (Abruf, Sprachen, Bilder, Browser-Maße).
- Doku: `docs/design.md` (Abschnitt Anmelde- und Kontoseiten, Infoseite), `docs/sprachen.md`.

## Bestehende Muster
- Reiseseite: Großansicht PhotoSwipe (`engine/vorlage.html`, `grossAnsicht`), Modul lädt erst beim Öffnen; bekannter Fehler #706 (`currSlide` beim `change` während des Öffnens undefiniert).
- Konnektorseiten: kein Inline-Skript (CSP `script-src 'self'`, `style-src 'unsafe-inline'` ohne `'self'`), Texte für Skripte über `data-texte` (konto.js).
- nginx-Ort `location ^~ /info/` führt schon alles unter /info/ zum Dienst: neue Seiten und Skripte dort brauchen keinen nginx-Schritt.

## Risiken
- CSP: externe Stilblätter sind gesperrt, PhotoSwipe-Stile müssen in die Seite.
- Pfade unter /info/ dürfen nichts anderes aus dem Ordner ausliefern (kein Weg hinaus).
- Scoping: Texte in zwei Sprachen sind umfangreich; Lieferung in zwei PRs (Galerie zuerst, dann Übersicht und Unterseite).

## Analysis

**Type:** Feature (Erklärseiten der Software, keine Reisedaten, keine Grundform; ADR-0001 unberührt).

**Lieferung in zwei PRs** (Scoping): PR 1 Galerie auf der Infoseite; PR 2 Übersicht „Alle Funktionen“, Muster-Unterseite
„Reiseseite“, Karte „Was Frieda alles kann“ statt des GitHub-Links, neue Bilder.

### Affected Files
| Datei | Änderung | PR |
|---|---|---|
| `engine/app/galerie.js` | CREATE: Skript der Galerie (PhotoSwipe lädt beim ersten Öffnen, Unterschrift-Streifen, #706 abgefangen) | 1 |
| `engine/anmeldung.py` | MODIFY: Markup `.bilder.reihe`, Stile, `info_datei` liefert auch Skript und PhotoSwipe-Modul; PR 2: Seiten, Routen, Datenform | 1, 2 |
| `engine/konnektor.py` | MODIFY: `/info/…` liefert Datei oder (Seiten) die Anmeldeseiten; Skripte ohne Tages-Cache | 1, 2 |
| `engine/texte_de.py`, `engine/texte_en.py` | MODIFY: neue Schlüssel `info.galerie.…`; PR 2 `info.funktionen.…`, `info.bereich.…` | 1, 2 |
| `engine/info/erzeugen.py` | MODIFY: Bilder der Unterseiten | 2 |
| `engine/tests/test_infoseite.py`, neue Browsertests | MODIFY/CREATE | 1, 2 |
| `docs/design.md`, `docs/sprachen.md` | MODIFY | 1, 2 |

### Technical Approach
- Wege: alles unter `/info/` (nginx-Ort vorhanden). `/info/galerie.js` aus `app/`, `/info/photoswipe-5.4.4.esm.min.js` aus `vendor/`;
  PhotoSwipe-Stile in der Seite (CSP erlaubt nur Inline-Stile). Seiten `/info/funktionen/` und `/info/funktionen/<bereich>/`.
- Texte des Skripts über `data-texte` (wie konto.js); Großansicht-Texte aus `seite.bild.*` wiederverwendet, Zähler und Wischhinweis neu.
- Form der Unterseiten (PR 2): ein Eintrag je Bereich in einer Tabelle in `anmeldung.py` (Bilder, Sprecher des Gesprächs, Siehe auch);
  Texte in `texte_<sprache>.py` unter `info.bereich.<name>.…`, nummerierte Listen werden aus dem Katalog gezählt.

### Risk
Niedrig bis mittel: nur öffentliche Erklärseiten; Wege unter /info/ müssen eng bleiben (feste Namen, kein Weg hinaus).

### Open Questions
Keine (Entwurf freigegeben, Technik entscheidet Claude).
