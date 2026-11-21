# Context: feature-582-eigene-fotos

## Request Summary
Bilder Stufe 2 aus dem Konzept in #455 (Weg B): Mitwirkende laden eigene Fotos hoch, auf der Reiseseite (angemeldet) und über einen kurzlebigen Link, den Claude im Chat über den Konnektor ausgibt. Beim Hochladen: HEIC → bearbeitbares Format, Drehung anwenden, alle Metadaten (GPS, Kamera) entfernen, Hinweis zu Personen auf Fotos (Seite ist per geheimem Link ohne Anmeldung lesbar). Eigene Fotos sind echt löschbar durch die hochladende Person und Organisator:innen; im Verlauf bleibt ein Eintrag ohne Bild. Grenzen je Datei und Reise. Beide Beispielreisen. Entwurf der Oberfläche als Artefakt vor dem Bauen (#436).

Entscheidungen des Product Owners:
- 15.11.2026 (#455 Abschnitt 9): Hinzufügen ab mitwirkend, Titelbild nur Organisator:innen; echtes Löschen eigener Fotos durch hochladende Person und Organisator:innen, Verlaufseintrag bleibt. Ausnahme zu ADR-0001 Frage 7 dort im Verlauf eintragen (wie #381, #12).
- 17.11.2026 (#582, #613): keine Prüfung und keine Bestätigung der Urheberschaft beim Hochladen; Verantwortung bei der hochladenden Person.
- Darstellung aus Stufe 1 (Variante A, Kopfbild, Galerie, Großansicht) ist freigegeben; neu zu zeigen sind nur Hochladen, Hinweis, Löschen und die Nennung „Foto: <Name>“.

## Related Files
| File | Relevance |
|------|-----------|
| `engine/bilder.py:6-21` | Schema eines Bildeintrags (`id`, `zu`, `quelle`, `urheber`, `lizenz`, `seite`, `bildunterschrift`, `alt`, `titelbild`, `status`, `dateien{klein,gross}`, `breite`, `hoehe`, `hinzugefuegt{datum,wer}`) → neue `quelle: eigen` (o. ä.) |
| `engine/bilder.py:53-59` | `MAX_BILD` 15 MB, `FASSUNGEN` 480/1600, `RASTER` (ohne HEIC), `ORDNER` medien/bilder, `LISTE` plan/bilder.yaml |
| `engine/bilder.py:209,252-298` | `raster_pruefen`, Vorab-Übergabe `vorab_schreiben/lesen` (`FR_BILD_VORAB`), `fassungen_schreiben` (exif_transpose, WebP q80, EXIF fällt weg) |
| `engine/schreiben.py:64,6209-6225` | `MAX_BODY` 64 KB je Anfrage an den Schreibweg (nur mit `X-Frieda-Dienst`) → Foto passt nicht durch; Vorab-Weg nötig |
| `engine/schreiben.py:85,5274-5335,5883-5935` | Aktion `bild`, `bild_titelbild_recht`, `bild_grenze` (nur Anzahl aktiver Bilder), `bild_eintrag`, `bild_hinzufuegen` (WebP in Arbeitskopie, `ordner_als_vorgang`), `bild_vorab` |
| `engine/reise.py:56-65,117-118` | `bilder: {max_anzahl: 60, offline_mb: 25}`; Aktionen `bild` (mitwirkend), `titelbild` (organisator) |
| `engine/rueckmeldungen.py:52-56,975-1011,1131-1145,1255-1275,1340-1382,1442` | Belege-Upload als Vorbild: `POST /<reise>/belege/<B>` roher Body + `X-Frieda-Datei`, `wer_ist` (Cookie `__Host-frieda`, Origin-Prüfung als CSRF-Schutz), `schreibrecht`, Drosselung 30/min, Ausliefern `private, no-store` |
| `engine/rueckmeldungen.py:253-286` | `rolle_aktuell` (fragt Schreibweg, wenn veröffentlichter Stand hinterherhinkt), `schreibrecht` |
| `engine/belege.py:26-56,122-176` | Grenzen 10 MB/Datei, 100 MB/200 Dateien je Reise; `typ_erkennen` (Magic Bytes inkl. HEIC-ftyp); kein echtes Löschen |
| `engine/konnektor.py:1896-1925,3277-3282,3458-3467` | `receipt_add`: base64 im Werkzeug → `beleg_senden` an Rückmeldedienst; Vorbild für Dienst-zu-Dienst-Weiterleitung |
| `engine/konten.py:70-165,318-363,1417-1456,1509-1520` | Tokens in `konten.db` nur als sha256-Hash mit `ablauf` (Anmeldecode 10 min, Einladung 30 Tage); Kalender-Abo als HMAC über Dienstgeheimnis → Muster für kurzlebigen Hochlade-Link |
| `engine/reisespeicher.py:8-30,124-142,190-195,252,841-919,951,1012-1030` | Nur anhängen (Trigger/Authorizer); Ablage `<aa>/<sha256>`; einzige Ausnahmen `reise_entfernen` und `namen_ersetzen`, `_ablage_aufraeumen`, `verdichten`, `sichern`; Quelltext-Test erlaubt nur diese |
| `docs/adr/0009-reisespeicher.md:19,50` | Ausnahmen vom Nur-anhängen, Löschprotokoll → dritte Ausnahme „Foto entfernen“ nötig |
| `engine/waechter.py:448` | `loeschungen_ausfuehren` (Ablauf des Reise-Löschens) |
| `engine/bauen.py:498-520,913,1527` | Nennung (`quelle: reise` → None), Warnung `offline_mb`, `bilder_schreiben` |
| `engine/vorlage.html:1517-1523,2274-2449,5150-5157` | `bildNennung`; Belege-Formular (`KANN_BELEG`, `belegeListe`, `form[data-bl-form]`, fetch POST roh) als Muster; `MIT_KONTO()`/`ICH` |
| `engine/sw.vorlage.js:96` | `/api/` nie aus dem Speicher |
| `engine/texte_*.py` (`seite.bild.*` de `:3881-3887`) | neue Texte: „Foto: <Name>“, Hochladen, Hinweis Personen, Löschen, Ablehnungen, Link-Seite |
| `betrieb/vorlagen/nginx-reise.conf:22-44` | `client_max_body_size 11m` nur für `api/belege/`; eigener Block für Fotos nötig |
| `engine/requirements.in`, `requirements.txt:893`, `THIRD_PARTY.md:14` | Pillow 13 (WebP, AVIF; kein HEIC). pillow-heif fehlt (BSD-3, bündelt libheif LGPL) |
| `betrieb/veroeffentlichen.sh:548-586` | Server baut neue venv bei geänderter `requirements.txt` und tauscht nach grünen Prüfungen |
| `betrieb/deploy.sh` | Modullisten, falls neues Modul |
| Tests: `test_rueckmeldungen.py:229-300`, `test_bilder.py`, `test_loeschen_reise.py:498`, `test_betrieb.py:2039`, `test_sicherheit.py:130,140`, `test_konnektor.py:962,1022`, Browser `seiten_bilder_p2.mjs`, `seiten_bilder_csp.mjs` | Muster; Browsertest mit echtem `setInputFiles` gibt es noch nicht |

## Existing Patterns
- **Datei-Upload von der Seite:** Rückmeldedienst nimmt rohen Body mit Header `X-Frieda-Datei`, prüft Sitzung (Cookie) und Origin, Rolle, Drosselung, Inhalt an Magic Bytes; nginx-Block mit größerem `client_max_body_size`.
- **Bilder in die Reise:** Schreibweg schreibt WebP-Fassungen in die Arbeitskopie, `ordner_als_vorgang`, Ablage lagert aus. Große Daten kommen am 64-KB-Limit vorbei über einen Vorab-Weg (`FR_BILD_VORAB`, Muster `kartenpunkte_vorab`).
- **Kurzlebige Tokens:** zufälliges Token, in `konten.db` nur als Hash mit Ablauf; oder HMAC über Dienstgeheimnis.
- **Echtes Löschen:** nur als ausdrückliche ADR-Ausnahme im Reisespeicher mit `_ablage_aufraeumen` + `verdichten` + Löschprotokoll.

## Dependencies
- Upstream: Pillow (+ HEIC-Bibliothek neu), Reisespeicher/Ablage, Konten (Sitzung, Rolle), Schreibweg, nginx.
- Downstream: Bau/Darstellung (Nennung eigener Fotos), Service Worker (gelöschte Bilder aus dem Cache), Export (#498), Reise löschen (#381), Sicherung (`sichern`, außer Haus), Konnektor-Anleitung, `docs/konnektor.md`, Instanz-Tests.

## Existing Specs
- `docs/specs/oberflaeche/bilder-455-stufe1.md` (Abgrenzung Stufe 2: `:24,44,89-90,205,316-317` – verwaiste Fassungen aufräumen ist Stufe 2)
- `docs/specs/oberflaeche/bilder-455-p2.md`, `bilder-455-p3.md`, `bilder-lizenzhinweis-613.md` (`:50,216` Verantwortungsangabe für eigene Fotos)
- `docs/specs/betrieb/loeschen-381.md`, `export-498.md`; ADR-0009, ADR-0001 (Frage 7, Verlauf der Ausnahmen)

## Risks & Considerations
- **Echtes Löschen gegen Nur-anhängen (ADR-0009):** braucht eine dritte, eng begrenzte Ausnahme (Bild-Blob aus allen Versionen entfernen, Tombstone im Verlauf). Daneben liegen Kopien in gebauter Seite, Sicherung (`sicherung/reisen.db`, außer Haus), Exporten, SW-Caches der Geräte → festlegen, was „gelöscht“ zusagt (Fristen für Sicherungen, ehrlicher Text).
- **Weg der Bytes:** Seite → Rückmeldedienst (hat Anmeldung) → Schreibweg (64-KB-Grenze). Optionen in der Analyse: Rückmeldedienst legt Datei vorab ab und gibt nur Verweis weiter; oder Schreibweg bekommt eigene Upload-Route mit höherer Grenze. Sicherheitsgrenze zwischen Diensten (`X-Frieda-Dienst`) wahren.
- **Kurzlebiger Link aus dem Chat:** Wer ihn hat, kann hochladen → an Person, Reise und Ziel-ID gebunden, kurze Laufzeit, Hash in `konten.db`, ggf. einmalig/Anzahl begrenzt; Seite des Links braucht CSP, kein Leak des geheimen Seitenlinks. Hochladen über Link ohne Anmeldung oder mit? (technisch zu entscheiden; Konzept: Person tippt Link am Handy).
- **HEIC:** neue Fremdbibliothek (pillow-heif, libheif LGPL) → `THIRD_PARTY.md`, Hashes in `requirements.txt`, venv-Tausch auf dem Server; Alternative: Browser wandelt um (Safari liefert beim Datei-Upload meist schon JPEG). Auf dem Server testen, dass das Rad für die Plattform existiert.
- **Metadaten:** WebP-Fassungen ohne EXIF sind schon so; Original nie speichern; Test, dass GPS weg ist.
- **Grenzen:** heute nur Anzahl je Reise; neu Größe je Datei (vor Verkleinerung) und je Reise; nginx-Block; Drosselung; Dekompressionsbombe (Pillow `MAX_IMAGE_PIXELS`).
- **Rechte:** Löschen nur hochladende Person oder Organisator:in; Rolle kann im veröffentlichten Stand hinterherhinken (`rolle_aktuell`).
- **Verwaiste Fassungen** nach gescheitertem Speichern aufräumen (offen aus Stufe 1).
- **Beide Beispielreisen:** Stadtwochenende ohne Bilder bekommt nur die Möglichkeit zum Hochladen, sonst unverändert.
- **Instanz-Tests** wegen neuer Texte, Routen, nginx, Paket vor dem Vorspulen laufen lassen.
- **Umfang groß:** in Pakete schneiden (z. B. P1 Hochladen auf der Seite + Metadaten + Grenzen, P2 Link aus dem Chat, P3 echtes Löschen, HEIC wo es hingehört).

## Analysis

### Type
Feature (groß, in drei Paketen)

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/bilder.py` | MODIFY | Quelle `eigen` (`quelle: {eigen: <sha>}`), Besitzkennung (Konto/Person, nicht nur Name in `hinzugefuegt.wer`), Grenzen je Datei und Summe je Reise, HEIC-Opener, `MAX_IMAGE_PIXELS`, Aufräumen verwaister Fassungen |
| `engine/schreiben.py` | MODIFY | eigene Route `POST /<reise>/bild_hochladen` (roher Body bis 12 MB, nur mit `X-Frieda-Dienst`, Metadaten als kleiner JSON-Header), getrennt von der JSON-Route mit `MAX_BODY` 64 KB; Dekodieren/WebP vor der Reisesperre (Vorab-Mechanik `FR_BILD_VORAB` wiederverwenden); Aktion Löschen mit Recht „hochladende Person oder Organisator:in“ |
| `engine/rueckmeldungen.py` | MODIFY | Upload-Route nach Muster `_beleg_hochladen` (Cookie + Origin, `rolle_aktuell`/`schreibrecht`, Drosselung, Größe, Magic Bytes), Weiterleitung an Schreibweg; Löschen (nur angemeldet); P2: Link-Seite und Upload per Token |
| `engine/reisespeicher.py` | MODIFY | dritte Ausnahme vom Nur-anhängen `bild_entfernen(reise, bid)`: in einer `BEGIN IMMEDIATE`-Transaktion Inhalte der beiden Pfade `medien/bilder/<bid>-480/-1600.webp` in allen Versionen leeren (Zeile bleibt, `inhalt`/`pruefsumme` NULL), `_ablage_aufraeumen`, `verdichten`, Neubau erzwingen; `pruefen`/`materialisieren`/Export tolerieren geleerte Zeilen |
| `engine/konten.py` | MODIFY (P2) | Tabelle für Hochlade-Tokens: sha256-Hash, Reise, Person, optional Ziel-ID, Ablauf 30 min, Restzähler 10 |
| `engine/konnektor.py` | MODIFY (P2) | Werkzeug, das den kurzlebigen Hochlade-Link ausgibt (englischer Name, deutscher Alias), Hinweis in der Anleitung |
| `engine/vorlage.html` | MODIFY | Hochladen (Formular nach Muster Belege), Hinweis zu Personen auf Fotos, Löschen, Nennung „Foto: <Name>“ |
| `engine/sw.vorlage.js` | MODIFY (P3) | gelöschte Bilder beim nächsten Laden aus dem Cache nehmen |
| `engine/bauen.py` | MODIFY | Nennung für Quelle `eigen` |
| `engine/texte_*.py` | MODIFY | alle neuen Texte in allen Sprachen |
| `engine/requirements.in`, `requirements.txt`, `THIRD_PARTY.md` | MODIFY | `pillow-heif` (BSD-3, bündelt libheif LGPL); Rad für cp312 manylinux_2_28 x86_64 vorhanden (1.8.1) |
| `betrieb/vorlagen/nginx-reise.conf` | MODIFY | eigener Block für Foto-Uploads mit `client_max_body_size` ~13m |
| `betrieb/deploy.sh` | CHECK | Modulliste nur, falls neues Modul |
| `docs/adr/0009-reisespeicher.md`, `docs/adr/0001-kern.md` | MODIFY | Ausnahme `bild_entfernen`; Verlauf der Ausnahmen zu Frage 7 |
| `docs/konnektor.md`, `docs/betrieb.md`, `docs/design.md` | MODIFY | Werkzeug, Löschen eigener Fotos in der Datenschutztabelle, Bausteine |
| `engine/neu.py` | CHECK | `nachziehen` nur, falls Format von `plan/bilder.yaml` sich ändert (Besitzkennung optional ⇒ alte Einträge gültig) |
| Tests: `test_bilder.py`, `test_rueckmeldungen.py`, `test_schreiben*`, `test_loeschen_reise.py` (Quelltext-Test der Ausnahmen `:606-609`, ADR-Prüfung), `test_konnektor.py`, `test_texte.py`, `test_betrieb.py`, Browser `seiten_bilder_*.mjs` | MODIFY/CREATE | GPS/EXIF weg, HEIC, Grenzen, Rechte, Token, Löschen inkl. zwei identische Uploads, beide Beispielreisen |

### Scope Assessment
- Files: ~25–30
- Estimated LoC: +1.400 bis +1.800 (inkl. Tests)
- Risk Level: HIGH (Ausnahme vom Nur-anhängen im Reisespeicher, neuer Upload-Weg ohne Anmeldung per Token, neue Fremdbibliothek mit Bilddekoder)

### Technical Approach (Entscheidungen des Tech Leads)
- **Weg der Bytes:** Browser → nginx-Block → Rückmeldedienst (Anmeldung, Rolle, Drosselung, Größe, Magic Bytes) → eigene Upload-Route des Schreibwegs (HTTP mit `X-Frieda-Dienst`). Keine Übergabe über Dateipfade zwischen Diensten (Dienstgrenze bleibt). Dekodieren vor der Sperre, Original nie gespeichert, WebP ohne EXIF.
- **HEIC auf dem Server** mit `pillow-heif` (alle Browser, testbar, Metadaten serverseitig kontrolliert); nur nach Magic-Bytes-Prüfung, `MAX_IMAGE_PIXELS`, Zeitgrenze. Glibc des Servers im Veröffentlichen-Lauf prüfen (Rad braucht ≥ 2.28). Browser-Umwandlung verworfen (nur Safari kann HEIC dekodieren, nicht testbar).
- **Link aus dem Chat (P2):** Token in `konten.db` als Hash mit Ablauf 30 min, höchstens 10 Fotos, gebunden an Reise und Person (ab mitwirkend, Rolle beim Hochladen neu geprüft); ohne Anmeldung nutzbar, aber nur zum Hochladen; Löschen immer mit Anmeldung. Link-Seite mit eigenem CSP und `Referrer-Policy: no-referrer`, ohne geheimen Seitenlink.
- **Echtes Löschen (P3):** dritte, eng begrenzte ADR-0009-Ausnahme (zwei feste Pfade je Bild, eine Transaktion, Aufräumen der Ablage, VACUUM, Neubau). Besitznachweis über eine Kennung, nicht über den Namen. Verlaufseintrag „Foto entfernt“ mit Datum und wer entfernt hat; das Bild selbst ist weg.
- **Zusage beim Löschen** folgt der bestehenden Regel aus #381 (`docs/betrieb.md:61`): sofort von Seite, Verlauf, Export und Speicher; Sicherungen bis zur Rotation, höchstens 30 Tage; Kopien auf Geräten anderer (schon heruntergeladen/offline) lassen sich nicht zurückholen, der Text sagt das ehrlich. Keine neue Produktentscheidung, nur Wortlaut im Entwurf.
- **Grenzen:** 12 MB je Datei vor der Verkleinerung; je Reise weiter `bilder.max_anzahl` (60) plus neue Summe der gespeicherten Fassungen (`bilder.max_mb`, Vorgabe 150) in `reise.yaml`; Drosselung wie Belege.
- **Pakete:** P1 Hochladen auf der Seite + Metadaten + Grenzen + HEIC; P3 Löschen; P2 Link aus dem Chat. Bau in der Reihenfolge P1 → P3 → P2; P1 geht erst zusammen mit P3 in den Betrieb (wer annimmt, muss löschen können). ADR-Ausnahme und Spec vor dem ersten Code; Oberflächen-Entwurf als Artefakt (#436) zur Freigabe in der Spec-Phase (Hochladen, Hinweis zu Personen, Löschen mit Zusage, „Foto: <Name>“, Link-Seite).

### Dependencies
- Upstream: Pillow 13 (+ pillow-heif neu), Reisespeicher/Ablage, Konten (Sitzung, Rolle, Tokens), Schreibweg, nginx.
- Downstream: Bau/Nennung, Service Worker, Export (#498), Reise löschen (#381, `namen_ersetzen`), Sicherung, Konnektor-Anleitung, Instanz-Tests (neue Texte, Routen, nginx, Paket ⇒ vor dem Vorspulen mitlaufen lassen).

### Risks
- Dekompressionsbomben/HEIC-Dekoderfehler → Pixelgrenze, Zeitgrenze, begrenzter Unterprozess.
- Weitergeleiteter Link → kurze Laufzeit, Zähler, Bindung an Person.
- Verwaiste Fassungen nach gescheitertem Speichern (offen aus Stufe 1) im selben Zug aufräumen.
- Zwei identische Uploads teilen einen Blob → Test.
- Langsame Uploads binden den Rückmeldedienst → Zeit- und Größenlimits.
- Stadtwochenende (ohne Bilder) bekommt nur die Möglichkeit zum Hochladen.

### Open Questions
- [ ] Wortlaut der Hinweise (Personen auf Fotos, Zusage beim Löschen) und Gestaltung: Freigabe über den Artefakt-Entwurf in der Spec-Phase (#436). Keine weiteren offenen Produktfragen; Grenzen, Link-Laufzeit und Verlaufseintrag sind technische Vorgaben (Begründung oben).
