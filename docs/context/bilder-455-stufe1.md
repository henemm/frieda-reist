# Context: bilder-455-stufe1

## Request Summary
Stufe 1 des Bildkonzepts aus #455 zusammen mit #581: Bilder werden ein eigener Teil der Reise mit Kennung, Zuordnung zu genau einer ID und Herkunft. Weg A: Claude nennt über den Konnektor eine Commons-Datei oder Wikidata-Kennung, Frieda holt das Bild selbst, prüft die Lizenz gegen eine Positivliste, legt es in die Ablage. Darstellung nach freigegebenem Entwurf (Titelbild Variante A über dem Titel, Kopfbild an der Heimat von Ort/Unterkunft/Etappe/Tag mit kleiner Bildreihe, Vorschaubild in Zeilen, Bild im Wissenstext, Namensnennung, Großansicht wischbar, Kachel in „Meine Reisen“). Bilder von fremden Adressen im Text werden gesperrt (#581).

Freigabe des Product Owners: Kommentar in #455 vom 15.11.2026 (Entwurf als privates Artefakt, Variante A). Entscheidungen im Issue-Text Abschnitt 9: Rechte „Bild hinzufügen ab mitwirkend, Titelbild nur Organisator:innen“; Stufe 2 (eigene Fotos, echtes Löschen) ist #582, nicht hier.

## Entwurf (freigegeben) – was die Seite zeigen soll
- **Titelbild (A):** Bild 16:10 mit großem Radius oben auf der Startseite, darunter Namensnennung klein, darunter der Reisekopf wie heute. In der Liste der Tage rechts ein Vorschaubild (44 px) bei Tagen mit Kopfbild; Tage ohne Bild unverändert.
- **Meine Reisen (Konto):** Kachel mit Titelbild (16:7); ohne Titelbild ruhige Fläche in Akzentfarbe mit dem App-Symbol der Reise, nie leerer Kasten. Heute gibt es dort **keine Kacheln**, nur Zeilen mit Titel und Rolle (`engine/anmeldung.py:1064–1090`) → Umbau der Liste nötig.
- **Kopfbild:** 16:9 über dem Namen an Ortsseite, Etappe (über den Kennzahlen), Tagesseite (über der großen Tageszahl), Unterkunft oben in ihrer Karte an der ersten Nacht. Weitere Bilder als Reihe kleiner Bilder (72×54) mit „n Bilder“. Andere Stellen (z. B. Unterkunft an Tag 3) nur Zeile mit Mini-Vorschaubild.
- **Wissenstext:** Bild in Spaltenbreite, Bildunterschrift (schreibt Claude), Namensnennung setzt Frieda selbst darunter. Bildlink im Satz auf ein Bild der Reise wird als Bild gezeigt (Ursprungsfrage #455: ja).
- **Großansicht:** dunkler Hintergrund, „Ort · 1 / 3“, Schließen, Pfeile (am Handy ausgeblendet), Wischen, Wischen nach unten schließt, Bildunterschrift und volle Nennung (Urheber · Lizenz als Link · Commons-Seite). Gruppe = Bilder desselben Dings. Offline: große Fassung.
- **Namensnennung:** Urheber · Lizenz (Link) · Commons; gemeinfrei nur Urheber. Eigene Fotos erst Stufe 2.
- **Reise ohne Bilder** (Stadtwochenende): exakt wie heute, keine Platzhalter.
- Entwurf-CSS (Klassen `bild titel|kopf|text`, `nennung`, `bildtext`, `galerie`, `mini`, `reisekachel`, `#gross`) liegt im Artefakt; Tokens entsprechen der Vorlage.

## Related Files
| File | Relevance |
|------|-----------|
| `engine/bauen.py:51,73` | `BILD_ENDUNGEN`, `BILD_LINK` |
| `engine/bauen.py:139` | `skripte_festlegen()` Meta-CSP ohne `img-src` → um `img-src 'self' data: blob:` ergänzen (#581); prüfen, was Karte/Kacheln (PMTiles, MapLibre, blob:) brauchen |
| `engine/bauen.py:162–193` | `TextPruefung`: `SCHEMATA` http/https/mailto/tel, `adresse_erlaubt` lässt `//host` und Schemata zu, auch für `img src` |
| `engine/bauen.py:401–464` | `html()`: `bilder_umschreiben` → Markdown → TextPruefung (`pruefung.bauen.5`) → nh3 → `<img loading=lazy>` → Vorschaubild bei Listenpunkt mit Bildlink (`:414`) |
| `engine/bauen.py:438–441` | `bilder_umschreiben()` lässt `xxx://` unverändert (Hotlink); Fehler `pruefung.bauen.7` (fehlt), `.8` (außerhalb) |
| `engine/bauen.py:1355` | `bilder_schreiben()`: max 1600 (`bilder_max_breite`), exif_transpose, JPEG q80 ohne EXIF, nur bei neuer Quelle |
| `engine/bauen.py:1399–1456` | `pwa_schreiben()`: Aufräumen `dist/medien`, Precache-Liste `dateien` inkl. `self.bilder`, `__DATEIEN__` in `sw.vorlage.js:22` |
| `engine/bauen.py:1599–1609` | App-Symbol `SYMBOL_DATEIEN`, `symbol_motiv`, `SYMBOL_MAX` 40 KB (für Kachel ohne Titelbild) |
| `engine/sw.vorlage.js:22,93` | Precache-Liste; bedient nur eigene Herkunft → Zwei-Stufen-Offline (klein alle, groß Titel/Kopf, Rest beim Ansehen) hier |
| `engine/vorlage.html` | Kopfkommentar Bausteine `:1397–1410`; Bild-CSS `:123–126`; `ansichtReise` `:3676` (Titelbereich `.reisekopf` `:3683`); `ansichtTag` `:4099`; `ansichtOrt` `:4163`; Unterkunft `nachtAbschnitt` `:4059`; Etappe `ansichtAbschnitt` `:4435`; `GRUNDFORMEN` `:4504–4534`; `ansichtBausteine` `:4565`; `heimat()` `:6101` |
| `engine/anmeldung.py:1064–1147` | `konto_seite()` „Meine Reisen“ (Zeilen, Archiv in `<details>`) → Kacheln; CSP dort `img-src 'self'` (`konnektor.py:3442`, `oauth.py:243 csp_fuer`) – Titelbild-URL muss von derselben Herkunft kommen |
| `engine/reisespeicher.py` | Ablage: `AUSLAGERN` (`:77`, png/jpg/jpeg/webp/gif/gpx/pmtiles), `ablage_ablegen` `:261`, `_eintragen` `:351`, `ordner_als_vorgang` `:433`, `materialisieren` `:632`, `exportieren` `:526`, `reise_entfernen`/`_ablage_aufraeumen` `:1060/1085`. Bilddateien unter `medien/` werden automatisch ausgelagert |
| `engine/schreiben.py` | `MAX_BODY` 64 KB `:67`; `AKTIONEN` `:80`; `DING_ARTEN`/`ID_MUSTER` `:1210`, `neue_id` `:1498`; Overpass-Muster `:2225–2310` (urllib, `instanz.kennung()`, timeout, eine Wiederholung bei 429/5xx); `symbol_setzen` `:3241` (Vorbild: Bytes in Arbeitskopie `medien/`, Pillow-Prüfung, dann Probebau und `ordner_als_vorgang` `:5267`); `WERKZEUGE` `:5065`; `anwenden_im_ordner` `:5194`; `kartenpunkte_vorab` `:5533` (Netzabruf vor der Sperre!) |
| `engine/konnektor.py` | Schemas (`SYMBOL_SETZEN` `:2793`), `ONTOLOGIE_WERKZEUGE` `:78`/`ONTOLOGIE_AKTION` `:88`, `werkzeuge_fuer` `:3324–3338`, `ontologie_werkzeug` `:1548`, `schreib_anfrage` `:1304` (120 s), `MitBild` `:403` (Vorschaubild an Claude zurück) |
| `engine/schnittstelle.py` | `NAMEN` `:15–88` (englisch → deutsch), `PARAMETER` `:91`, `PARAMETER_JE_WERKZEUG` `:123` |
| `engine/reise.py:93–133` | `AKTIONEN` (Mindestrolle): neue Aktion für Bild (mitwirkend) und Titelbild (organisator) |
| `engine/neu.py` | `ARTEN` `:53` (W F O U A E T V B G) – neuer Präfix (`BI`) hier; `_nummern` `:109`; `nachziehen` `:963`, Schrittmuster `reste_nachziehen` `:1428`; `nachziehen_speicher` `:1147` |
| `engine/routen.py:36,184` | `MUSTER`, `GRUNDFORMEN` – Bild ist keine Grundform, sondern Eigenschaft (Konzept 3.1) |
| `engine/packliste.py` + Commits `2010199`, `707dd41` | Muster für eine neue Liste der Reise (`plan/packliste.yaml`): Modul, deploy-Liste, bauen, konnektor, neu, reise, routen, schreiben, schnittstelle, Texte, Tests |
| `engine/instanz.py:30,189` | `KENNUNG`/`kennung()` (`FR_KENNUNG`) als User-Agent für Commons |
| `engine/texte_*.py`, `engine/tests/test_texte.py` | alle Katalogtexte (Werkzeugbeschreibung, Ablehnungen, Nennung, Seite) in allen Sprachen |
| `betrieb/deploy.sh:26–35` | `KN_MODULE`, `SB_MODULE` – neues Modul (z. B. `bilder.py`) eintragen; `test_betrieb.py:1508` prüft |
| `betrieb/vorlagen/nginx-reise.conf` | keine CSP; Cache-Regeln für `medien/` |
| `beispiel/reisen/beispielreise/` | `medien/skizze-felsen.png`, Bildlink `inhalt/etappen.md:46`; Beispielreise braucht freie Beispielbilder (klein, im Repo, mit Lizenz/THIRD_PARTY) |
| `beispiel/reisen/stadtwochenende/` | ohne Bilder – muss unverändert bleiben |
| `docs/design.md`, `docs/konnektor.md`, `docs/ontologie.md`, `docs/adr/0003-heimat.md` | Bausteine, Werkzeugliste (`test_design.py:175` prüft Gleichstand), Heimat |

## Existing Patterns
- **Binärdaten über den Schreibweg:** `symbol_setzen` schreibt Bytes in die Arbeitskopie `medien/`; Probebau; `ordner_als_vorgang` macht daraus einen Vorgang; die Ablage lagert Bilder automatisch aus (Prüfsumme). Bilder für Stufe 1 können genauso landen – nur dass der Schreibweg die Bytes selbst aus Commons holt.
- **Netzabruf im Schreibweg:** Overpass (`overpass_senden` mit `instanz.kennung()`, Zeitlimit, Wiederholung) und `kartenpunkte_vorab` (Abruf vor der Schreibsperre, Ergebnis per Umgebung an den Unterprozess). Commons-Abruf sollte dem folgen (nicht unter der Sperre warten). Tests ersetzen die Abruffunktion per `monkeypatch` bzw. `urllib.request.urlopen`.
- **64-KB-Grenze** in Konnektor, Schreibweg und nginx → Bild nie als Base64 durchs Gespräch; Werkzeug bekommt nur Dateiname/Q-Kennung.
- **Antwort mit Bild an Claude:** `MitBild` (Vorschaubild zur Kontrolle nach dem Eintragen).
- **Neue Liste der Reise:** Muster Packliste (`plan/packliste.yaml`, Modul, Präfix in `neu.ARTEN`, Aktion in `reise.AKTIONEN`, Werkzeuge in drei Registern, Bausteine in Vorlage + `docs/design.md`).
- **Formatwechsel:** neuer Schritt `bilder_nachziehen` in `neu.nachziehen` mit Test (Altbestand `medien/…` im Text → Bild mit Herkunft „aus der Reise übernommen“; Hotlink im Text → Link, #581).
- **Bau:** Bilder werden heute nur verkleinert (JPEG q80). Konzept will zwei Fassungen als WebP (480/1600). Pillow kann WebP.

## Dependencies
- Upstream: Pillow, `urllib.request`, Wikimedia Commons API (`action=query&prop=imageinfo&iiprop=url|extmetadata|mime|size&iiurlwidth=1600`), Wikidata (`wbgetclaims` P18), Ablage/Reisespeicher, `instanz.kennung()`.
- Downstream: Generator (Daten an Vorlage), Vorlage (Bausteine), Service Worker, Konto-Seite, Export (Medien kommen über `exportieren` mit), Löschen (`_ablage_aufraeumen`), `neu.py nachziehen`, Konnektor-Anleitung/`docs/konnektor.md`, Instanz-Tests (Meldungstexte, Format).

## Existing Specs
- `docs/specs/betrieb/speicher-349-stufe4.md` (Ablage, keine Größenschwelle), `speicher-350-stufe5.md`
- `docs/specs/oberflaeche/packliste-431.md`, `docs/adr/0010-gegenstand.md` (Muster neue Liste)
- `docs/specs/betrieb/export-498.md`, `loeschen-381.md`
- Zu Bildern/Commons gibt es noch keine Spec.

## Risks & Considerations
- **Kern (ADR-0001):** Bild ist keine Grundform, keine Art, kein Merkmal, sondern Eigenschaft der Grundformen mit eigener Liste; Lizenzregel prüft Frieda (deterministisch), Claude wählt nur aus.
- **Präfix:** `B-` ist Buchung. `BI-` muss in `neu.ARTEN`, `_nummern`-Regex und alle ID-Muster passen, ohne mit `B-` zu kollidieren (Regex `B-\d+` darf `BI-03` nicht treffen und umgekehrt).
- **Hotlink-Sperre bricht Bestand:** `test_sicherheit.py:31–34` verlangt heute, dass `https`- und `//`-Bilder durchgehen → Test anpassen; vorhandene Texte echter Reisen über `nachziehen` umstellen (Bild → Link), sonst bricht Veröffentlichen.
- **CSP `img-src`:** Karte nutzt MapLibre mit PMTiles (blob:, data:), Kartensymbole evtl. data:; vorher prüfen, Browser-Rundgang mit Karte.
- **Lizenz-Positivliste:** CC0, PD/Public domain, CC BY x.y, CC BY-SA x.y; abgelehnt: Free Art License (Befund im Issue), CC BY-NC/ND, GFDL-only, unbekannt. `extmetadata` `LicenseShortName`, `License`, `LicenseUrl`, `Artist` (HTML → Text säubern), `Credit`, `AttributionRequired`. Urheber-HTML nie ungesäubert auf die Seite.
- **Netz im Schreibweg:** Zeitlimit, User-Agent nach Wikimedia-Regeln, Anfragen nacheinander; nicht unter der Schreibsperre lange warten; klare Katalogtexte bei Nicht-gefunden, kein Bild (SVG/Video/PDF), unfreie Lizenz, Netzfehler. Thumbnail (≤1600 px) laden, nicht das Original; Größe begrenzen; Pillow-Prüfung am Inhalt.
- **Grenzen:** Ablage hat keine Größengrenze; Grenze je Reise (Anzahl/Summe, Offline 25 MB, in `reise.yaml` änderbar) neu einführen; Bau warnt bei Überschreitung.
- **Zwei Fassungen/WebP:** ändert `bilder_schreiben` und Precache; Altbestand (`skizze-felsen.png`) muss weiter gehen; Tests `test_bauen.py:224`, `test_pwa.py`.
- **„Meine Reisen“-Kacheln:** Konto-Seite wird vom Konnektor-Dienst ausgeliefert, CSP `img-src 'self'`; Titelbild liegt auf der Reiseseite (andere Pfade, ggf. anderer Host je Instanz). Wie die Kachel an das Bild kommt (Pfad unter derselben Domain, kleine Fassung) ist in der Analyse zu klären. Seite ist hinter Anmeldung; Reiseseite per geheimem Link – Bildpfad darf den geheimen Link nicht verraten (nur an Mitglieder ausgeliefert, die ihn ohnehin haben).
- **Heimat (ADR-0003):** Kopfbild nur an der Heimat, sonst Mini-Vorschaubild in Zeile; Unterkunft: Heimat ist die erste Nacht.
- **Mehrsprachigkeit:** alle sichtbaren Texte (Nennung „Foto:“, „n Bilder“, „Schließen“, Großansicht-Beschriftungen, Ablehnungen) in allen `texte_*.py`.
- **Beispielreise:** braucht echte freie Bilder (klein) mit Lizenz, in `THIRD_PARTY.md` vermerkt; Tests nie mit Netz – Commons-Antworten als Testdaten.
- **Instanz-Tests:** neue Meldungstexte und Datenformat → vor dem Vorspulen Tests der einbindenden Instanz mit dem Branch laufen lassen.
- **Umfang:** sehr groß (Format, Werkzeug, Netzabruf, Bau, Vorlage, Konto, SW, nachziehen, #581). In der Analyse in Pakete schneiden (wie Packliste: Paket 1 Daten+Werkzeug+#581, Paket 2 Darstellung, Paket 3 Doku/Konto).

## Analysis

### Type
Feature (mit Sicherheitsanteil #581)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/bilder.py` | CREATE | Liste der Bilder (`plan/bilder.yaml`), Commons/Wikidata-Abruf (`commons_info`, `herunterladen`, User-Agent `instanz.kennung()`, Zeitlimit, eine Wiederholung), Lizenz-Positivliste, Urheber-HTML säubern, Pillow-Prüfung, zwei WebP-Fassungen 480/1600, Lesefunktion Titelbild |
| `engine/neu.py` | MODIFY | `ARTEN` + `BI`; `nachziehen` Schritt `bilder_nachziehen` (Altbestand `medien/…` im Text → Bild „aus der Reise übernommen“, Hotlink-Bild → Link) |
| `engine/routen.py` | MODIFY | `MUSTER` um `BI-\d+` |
| `engine/schreiben.py` | MODIFY | `ID_MUSTER`; Vorab-Abruf nach Muster `kartenpunkte_vorab` (Netz vor der Sperre, Ergebnis als Datei in `vorab`); Aktionen `image_add`/Bild ändern/zurückziehen/Titelbild; Bytes in Arbeitskopie `medien/`, Probebau, `ordner_als_vorgang` |
| `engine/reise.py` | MODIFY | `AKTIONEN`: Bild ab mitwirkend, Titelbild organisator |
| `engine/konnektor.py`, `engine/schnittstelle.py` | MODIFY | Werkzeug `image_add` (+ Ändern/Zurückziehen), deutsche Aliase, `MitBild`-Vorschau zurück an Claude; P3: angemeldete Route `/bild/<reise>/<BI>.webp` (Mitgliedschaft, `Cache-Control: private`, Vorbild `/info/` `:3459`) |
| `engine/bauen.py` | MODIFY | #581: `TextPruefung` für `img src` nur `medien/…`/`BI-…`; Meta-CSP `img-src 'self' data:` (`:139`); P2: Bilddaten an Vorlage, `![](BI-03)`, Fassungen kopieren, Precache, Warnung Offline-Grenze |
| `engine/vorlage.html` | MODIFY | Bausteine Titelbild, Kopfbild + Bildreihe, Mini-Vorschau (Zeilen, Tagesliste), Bild im Text mit Nennung, Großansicht; Kopfkommentar, Bausteinseite |
| `engine/sw.vorlage.js` | MODIFY | zweistufiges Offline (klein alle, groß Titel/Kopf, Rest beim Ansehen) |
| `engine/anmeldung.py` | MODIFY | „Meine Reisen“ als Kacheln (Titelbild über Konto-Route, sonst Akzentfläche mit App-Symbol) |
| `engine/texte_*.py` | MODIFY | Werkzeugbeschreibung, Ablehnungen, Nennung, Großansicht, „n Bilder“ in allen Sprachen |
| `betrieb/deploy.sh` | MODIFY | `bilder.py` in `KN_MODULE`/`SB_MODULE` |
| `beispiel/reisen/beispielreise/` + `THIRD_PARTY.md` | MODIFY | kleine freie Beispielbilder mit Lizenz; Stadtwochenende unverändert |
| `docs/konnektor.md`, `docs/design.md`, `docs/ontologie.md`, ADR-0001-Verlauf | MODIFY | Werkzeug, Bausteine, Bild als Eigenschaft der Grundformen |
| `engine/tests/test_bilder.py` (+ Fixtures Commons-JSON, kleines Bild) | CREATE | Lizenzregel, Abruf per monkeypatch, Werkzeug, nachziehen, Hotlink-Sperre, CSP, Bau, Konto-Route |
| `engine/tests/test_sicherheit.py`, `test_design.py:175`, `test_betrieb.py:1508` | MODIFY | neue Sperrtests, Werkzeugliste, Modulliste |

### Scope Assessment
- Files: ca. 25 (in drei Paketen)
- Estimated LoC: P1 +1500–1800, P2 +1500–2000 (größtenteils Vorlage), P3 +300–500
- Risk Level: MEDIUM-HIGH (Datenformat für alle Reisen, Sperre kann echte Reisen mit Netz-Bildern brechen, CSP der Reiseseite, großer Oberflächenanteil)

### Technical Approach
Bewertung (Plan-Agent, Code gelesen 15.11.2026), angenommen:

- **Drei Pakete in fester Reihenfolge, je eigener PR, je für sich lieferbar:**
  - **P1 Daten + Werkzeug + #581 + nachziehen:** Liste, `BI-`, Rechte, Commons-Abruf vorab, Positivliste, beide WebP-Fassungen **schon beim Anlegen** in der Ablage (nicht erst im Bau: Bau bleibt deterministisch und kopiert nur; Konto-Route hat die kleine Fassung ohne Bau). Hotlink-Sperre und `bilder_nachziehen` zwingend im selben PR (sonst scheitert der Bau echter Reisen). Bau ignoriert Bilder-Liste noch.
  - **P2 Bau + Darstellung + Service Worker** nach freigegebenem Entwurf; Browser-Rundgang mit Karte (CSP), Belegen, Großansicht, beiden Beispielreisen.
  - **P3 Konto-Kachel + Doku.**
- **CSP:** einzige Stelle ist die Meta in `bauen.py:139–149` (kein `default-src`/`img-src` heute; nginx setzt keine). Karte ist Leaflet + protomaps (Canvas, `divIcon`s), `data:` nötig für das Ebenen-Symbol als CSS-`url(data:…)` (`vorlage.html:796`). → `img-src 'self' data:`; `blob:` nur, wenn der Rundgang es zeigt.
- **Kachel-Bild:** `seiten.json` enthält den geheimen Link je Reise (vom Betrieb beim Freischalten geschrieben, `konnektor.py:2063`), Host je Instanz möglich → `img-src 'self'` der Konto-Seite würde ein Bild von dort blockieren. Darum eigene angemeldete Konnektor-Route mit Mitgliedschaftsprüfung; geheimer Link taucht nicht auf, unabhängig vom Veröffentlichen. Base64 in der Seite abgelehnt.
- **Präfix `BI-`:** keine Kollision. `neu.py:109` `(?<![A-Za-z0-9])B-(\d+)`, `B-\d+`-Prüfungen in `schreiben.py:3653,5334`, `konnektor.py:1618,3159` sind `fullmatch`. Generische `[A-Z]+-\d+` (`schreiben.py:5248`), `[A-Z]{1,2}-` (`rueckmeldungen.py:398`) passen auf `BI-` (gewollt). `vorlage.html:3738` (Sprungmarken) erkennt `BI-` bewusst nicht. Zu ändern: `ARTEN`, `MUSTER`, `ID_MUSTER`; Tests mit Liste aller Arten suchen.
- **Altbestand:** Pipeline `bilder_schreiben` für `medien/…` (JPEG) bleibt unverändert (`test_bauen.py:226–235,670`, `test_pwa.py:59,98` bleiben grün); WebP nur für die neue Liste. Nach `nachziehen` stehen Altbilder ohnehin als `BI-` im Text.
- **Netz im Test:** nie; `monkeypatch` auf die zwei Netzfunktionen, Commons-Antworten als Fixtures.

### Dependencies
- P2 braucht das Format aus P1; P3 braucht 480er-Fassung und Titelbild-Kennung aus P1.
- Upstream: Pillow (WebP), `urllib.request`, Commons-API (`imageinfo`/`extmetadata`, `iiurlwidth=1600`), Wikidata P18, Reisespeicher-Ablage, `instanz.kennung()`.
- Downstream: Instanz-Tests (neue Meldungstexte, Datenformat) vor jedem Vorspulen mit dem Branch laufen lassen.

### Risks
- Echte Reisen mit Netz-Bildern: `nachziehen` im selben Commit wie die Sperre.
- CSP blockiert Ebenen-Symbol/Belege/Symbol, wenn `data:` fehlt → Rundgang.
- 64-KB-Grenze: nur Dateiname/Q durchs Gespräch.
- Commons-Ausfall/Rate-Limit: Zeitlimit, klare Katalogtexte, nicht unter der Schreibsperre warten.
- Urheberfeld ist HTML: säubern, nie roh ausliefern.
- Ablage ohne Grenze: Obergrenze je Reise (Anzahl/Summe), Offline 25 MB mit Warnung im Bau, in `reise.yaml` änderbar.

### Open Questions
- Keine Produktfrage offen (Entwurf, Variante A, Rechte, Stufentrennung entschieden 15.11.2026).
- Für die Spec festzulegen (technisch, Claude entscheidet): genaue Grenzwerte je Reise (Vorschlag 60 Bilder / 25 MB offline), Werkzeugschnitt (`image_add` + `image_update` mit Zurückziehen/Titelbild), Felder in `plan/bilder.yaml`.
