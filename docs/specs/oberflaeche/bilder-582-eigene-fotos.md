---
entity_id: bilder-582-eigene-fotos
type: feature
created: 2026-11-21
updated: 2026-11-21
status: draft
workflow: feature-582-eigene-fotos
version: "1.0"
tags: [bilder, hochladen, eigene-fotos, loeschen, heic, metadaten, konnektor, reisespeicher, datenschutz]
---

# Bilder Stufe 2: Eigene Fotos hochladen, von der Seite und über einen Link aus dem Chat (#582)

## Approval

- [ ] Approved

## Purpose

Stufe 1 (#455) zeigt Bilder aus Wikimedia Commons. Stufe 2 lässt Mitwirkende der Reise eigene Fotos hinzufügen: auf der Reiseseite (angemeldet) und über einen kurzlebigen Link, den Frieda im Chat über den Konnektor ausgibt. Beim Hochladen wird das Foto in zwei WebP-Fassungen umgewandelt (Drehung angewendet, alle Metadaten wie GPS und Kamera entfernt), das Original wird nie gespeichert. Die hochladende Person bekommt einen Hinweis zu Personen auf Fotos, weil die Seite per geheimem Link ohne Anmeldung lesbar ist. Eigene Fotos sind echt löschbar, durch die hochladende Person und durch Organisator:innen; im Verlauf bleibt ein Eintrag „Foto entfernt“ ohne Bild. Ohne Löschen darf es kein Hochladen geben, deshalb gehen P1 und P3 nur zusammen in den Betrieb.

Entscheidungen des Product Owners, verbindlich:

- **15.11.2026 (#455, Abschnitt 9):** Hinzufügen ab Rolle mitwirkend; Titelbild nur Organisator:innen; echtes Löschen eigener Fotos durch die hochladende Person und durch Organisator:innen; der Verlaufseintrag bleibt; die Ausnahme zu ADR-0001 Frage 7 wird im Verlauf von ADR-0001 eingetragen (wie bei #381 und #12).
- **17.11.2026 (#582, #613):** Keine Prüfung und keine Bestätigung der Urheberschaft beim Hochladen. Die Verantwortung liegt bei der hochladenden Person; es gilt der Hinweis aus `docs/specs/oberflaeche/bilder-lizenzhinweis-613.md`.
- **Darstellung aus Stufe 1** (Variante A, Kopfbild, Galerie, Großansicht) ist freigegeben und bleibt. Neu zu zeigen sind nur Hochladen, Hinweis zu Personen, Löschen mit Zusage, die Nennung „Foto: <Name>“ und die Link-Seite (siehe V17).

## Source

- **Kontext und Analyse (verbindlich):** `docs/context/feature-582-eigene-fotos.md`, Abschnitte „Analysis“ und „Technical Approach“.
- **Übergeordnete Specs:** `docs/specs/oberflaeche/bilder-455-stufe1.md` (Abgrenzung: eigene Fotos und Aufräumen verwaister Fassungen sind Stufe 2), `bilder-455-p2.md` (Darstellung, `daten.json`), `bilder-455-p3.md` (Bildroute `/bild/`, Kachel), `bilder-lizenzhinweis-613.md` (Verantwortungsangabe für eigene Fotos), `docs/specs/betrieb/loeschen-381.md` (Zusage beim Löschen, `namen_ersetzen`), `docs/specs/betrieb/export-498.md`.
- **Files (Zeilen geprüft am 21.11.2026):** `engine/bilder.py` (`MAX_BILD` Z. 53, `FASSUNGEN` Z. 56, `VORAB_UMGEBUNG` Z. 66, Vorab-Übergabe ab Z. 253), `engine/schreiben.py` (`MAX_BODY` Z. 64 und Prüfung Z. 6219, `bild_grenze` Z. 5280, `bild_hinzufuegen` Z. 5318, `bild_vorab` Z. 5883), `engine/rueckmeldungen.py` (`rolle_aktuell` Z. 253, `schreibrecht` Z. 280, `_beleg_hochladen` Z. 1340), `engine/reisespeicher.py` (`reise_entfernen` Z. 879, `_ablage_aufraeumen` Z. 904, `namen_ersetzen` Z. 951, `verdichten` Z. 1012), `engine/belege.py` (`typ_erkennen`), `engine/konten.py`, `engine/konnektor.py`, `engine/vorlage.html`, `engine/sw.vorlage.js`, `engine/bauen.py`, `engine/reise.py`, `betrieb/vorlagen/nginx-reise.conf`, `betrieb/veroeffentlichen.sh`, `betrieb/deploy.sh`.
- **Kern (ADR-0001):** Das Bild bleibt Eigenschaft der Grundformen mit eigener Liste `plan/bilder.yaml`; keine neue Grundform, keine Art, kein Merkmal, keine KI in Frieda.

## Dependencies

| Abhängigkeit | Art | Bedeutung |
|---|---|---|
| Stufe 1 (#455, P1 bis P3) und #613 | Voraussetzung | Datenformat, `bilder.py`, Darstellung, Bildroute, Hinweis zur Verantwortung; alles auf `main` |
| Pillow 13 | Fremdbibliothek, vorhanden | WebP-Fassungen, `exif_transpose`, `MAX_IMAGE_PIXELS` |
| `pillow-heif` (BSD-3, bündelt libheif unter LGPL) | Fremdbibliothek, neu | HEIC lesen; Eintrag in `THIRD_PARTY.md` und `engine/requirements.in`, Hashes in `requirements.txt`; Rad für cp312 manylinux_2_28 x86_64 (Version 1.8.1) vorhanden |
| Reisespeicher (ADR-0009) | intern | Ablage `<aa>/<sha256>`, nur anhängen; dritte Ausnahme `bild_entfernen` |
| Rückmeldedienst (`rolle_aktuell`, `schreibrecht`, Cookie `__Host-frieda`, Origin-Prüfung, Drosselung) | intern | Annahme der Bytes, Muster `_beleg_hochladen` |
| Schreibweg (`X-Frieda-Dienst`) | intern | eigene Upload-Route, getrennt von `MAX_BODY` |
| `konten.db` (Tokens nur als Hash, wie Anmeldecode und Einladung) | intern | Hochlade-Token (P2) |
| nginx-Vorlage der Reise | Betrieb | eigener Block mit `client_max_body_size` etwa 13m |
| Regel aus #381, `docs/betrieb.md` (Datenschutztabelle, Sicherungen höchstens 30 Tage) | Anforderung | Zusage beim Löschen |
| Export (#498), Reise löschen (#381, `namen_ersetzen`), Sicherung | Downstream | müssen geleerte Bildzeilen und Besitzkennungen vertragen |
| Playwright (Chromium, WebKit) | Testwerkzeug | erster Browsertest mit echtem `setInputFiles` |
| Tests der einbindenden Instanz | Betrieb | vor dem Vorspulen mit dem Branch (neue Texte, Routen, nginx-Block, Paket) |
| Freigegebener Entwurf (Claude-Artefakt, #436) | Anforderung | Wortlaut und Gestaltung der neuen Oberfläche, siehe V17 |

## Scope

Drei Pakete in Bau-Reihenfolge **P1, P3, P2**. P1 geht nur zusammen mit P3 in den Betrieb (wer annimmt, muss löschen können). P2 ist unabhängig auslieferbar.

- **P1:** Hochladen auf der Reiseseite, HEIC, Metadaten, Grenzen, Besitzkennung, Nennung, Hinweis zu Personen, Aufräumen verwaister Fassungen.
- **P3:** Echtes Löschen (dritte ADR-0009-Ausnahme `bild_entfernen`), Verlaufseintrag, Zusage, Service Worker, Doku-Zusagen.
- **P2:** Werkzeug im Konnektor, das einen kurzlebigen Hochlade-Link ausgibt; Link-Seite mit Token.

**Nicht im Scope:** Prüfung der Urheberschaft (Entscheidung 17.11.2026), Bildbearbeitung, Zuschneiden, mehrere Titelbilder, Videos, Hochladen ohne Konto und ohne Token, Bildunterschrift-KI, Gesichtserkennung, Zurückholen von Kopien auf fremden Geräten.

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/bilder.py` | MODIFY | Quelle `eigen`, Besitzkennung, Grenzen je Datei und je Reise, HEIC-Opener, `MAX_IMAGE_PIXELS`, Zeitgrenze, Aufräumen verwaister Fassungen |
| `engine/schreiben.py` | MODIFY | Upload-Route `POST /<reise>/bild_hochladen` (roher Body, nur mit `X-Frieda-Dienst`); Aktion Löschen mit Recht „hochladende Person oder Organisator:in“; Dekodieren vor der Reisesperre (Mechanik `FR_BILD_VORAB`) |
| `engine/rueckmeldungen.py` | MODIFY | `POST /<reise>/bilder/hochladen` nach Muster `_beleg_hochladen`; Löschen (nur angemeldet); P2: Link-Seite und Upload per Token |
| `engine/reisespeicher.py` | MODIFY | `bild_entfernen(reise, bid)` als dritte Ausnahme; `pruefen`, `materialisieren`, Export vertragen geleerte Zeilen |
| `engine/konten.py` | MODIFY (P2) | Tabelle der Hochlade-Tokens (Hash, Reise, Person, Ablauf, Restzähler); Aufräumen abgelaufener Tokens; Konto löschen räumt Tokens ab |
| `engine/konnektor.py` | MODIFY (P2) | Werkzeug `image_upload_link` (deutscher Alias nach dem Muster der übrigen Werkzeuge), Hinweis in der Anleitung |
| `engine/schnittstelle.py` | MODIFY (P2) | englischer Name mit deutschem Alias für das neue Werkzeug |
| `engine/reise.py` | MODIFY | `bilder.max_mb` (Vorgabe 150) neben `max_anzahl` (60) und `offline_mb` |
| `engine/vorlage.html` | MODIFY | Hochladen (Formular nach Muster Belege), Hinweis, Löschen mit Zusage, Nennung „Foto: <Name>“, Anzeige der Ablehnungen |
| `engine/sw.vorlage.js` | MODIFY (P3) | gelöschte Bilder beim nächsten Laden aus dem Cache nehmen |
| `engine/bauen.py` | MODIFY | Nennung für Quelle `eigen` (Z. 498 ff.), Verlaufseintrag „Foto entfernt“ in `daten.json` |
| `engine/texte_de.py`, `engine/texte_en.py`, alle weiteren `engine/texte_<kürzel>.py` | MODIFY | alle neuen Texte in allen Sprachen (Tabelle V17) |
| `engine/requirements.in`, `engine/requirements.txt`, `THIRD_PARTY.md` | MODIFY | `pillow-heif` mit Lizenz und Hashes |
| `betrieb/vorlagen/nginx-reise.conf` | MODIFY | eigener Block für Foto-Uploads, `client_max_body_size` etwa 13m |
| `betrieb/veroeffentlichen.sh` | MODIFY | Prüfung der Glibc (Rad braucht mindestens 2.28) vor dem Tausch der venv |
| `betrieb/deploy.sh` | CHECK | Modulliste nur ändern, falls ein neues Modul entsteht (dann ändern, ein Test prüft das) |
| `engine/neu.py` | CHECK | `nachziehen` nur, falls sich das Format von `plan/bilder.yaml` ändert; neue Felder sind optional, alte Einträge bleiben gültig |
| `docs/adr/0009-reisespeicher.md` | MODIFY | dritte Ausnahme `bild_entfernen` und Löschprotokoll |
| `docs/adr/0001-kern.md` | MODIFY | Verlauf: Ausnahme zu Frage 7 (Verlaufseintrag bleibt, Bild weg), Entscheidungen 15. und 17.11.2026 |
| `docs/konnektor.md` | MODIFY | Werkzeug, Hochlade-Route, Link-Seite |
| `docs/betrieb.md` | MODIFY | Datenschutztabelle: Löschen eigener Fotos, Grenzen, Aufbewahrung |
| `docs/design.md` | MODIFY | Bausteine Hochladen, Hinweis, Löschen, Nennung, Link-Seite |
| `engine/tests/test_bilder.py`, `test_rueckmeldungen.py`, `test_schreiben*.py`, `test_loeschen_reise.py`, `test_konnektor.py`, `test_texte.py`, `test_betrieb.py`, `test_sicherheit.py` | MODIFY | siehe Test Plan |
| `engine/tests/test_bilder_eigen.py`, `engine/tests/seiten_bilder_eigen.mjs` | CREATE | Hauptprüfungen und Browsertest |

### Estimated Changes

- Files: etwa 28
- LoC: +1.600/-60 (davon rund 700 Tests, rund 150 Doku und Texte)

## Implementation Details

Technische Entscheidungen des Tech Leads, nicht neu zu verhandeln.

### Weg der Bytes (alle Pakete)

Browser, dann nginx-Block (`client_max_body_size` etwa 13m, nur für den Foto-Ort), dann Rückmeldedienst (Cookie und Origin-Prüfung, Rolle über `rolle_aktuell`, Drosselung, Größe, Magic Bytes), dann eigene Upload-Route des Schreibwegs mit `X-Frieda-Dienst` (roher Body, Metadaten als kleiner JSON-Kopf `X-Frieda-Bild`). Diese Route ist von der JSON-Route mit `MAX_BODY` (64 KB) getrennt. **Keine Dateipfad-Übergabe zwischen den Diensten**; die Dienstgrenze bleibt. Dekodieren und WebP-Erzeugen geschehen vor der Reisesperre (Muster `FR_BILD_VORAB`), das Schreiben der Fassungen in die Arbeitskopie danach (`bild_hinzufuegen`, `ordner_als_vorgang`).

### Verarbeitung des Fotos (P1)

1. Größe: höchstens 12 MB je Datei, geprüft vor jeder Verkleinerung und schon am nginx-Block (13m lässt Kopf und Rahmen zu).
2. Format an den Magic Bytes (`belege.typ_erkennen`, inklusive HEIC-`ftyp`), nie am Dateinamen oder am Header des Browsers. Erlaubt: JPEG, PNG, WebP, HEIC/HEIF. Alles andere wird abgelehnt.
3. Dekompressionsbomben: `Image.MAX_IMAGE_PIXELS` fest gesetzt (Vorgabe 60 Megapixel), Zeitgrenze für das Dekodieren, bei HEIC begrenzter Unterprozess; Überschreitung heißt Ablehnung „Format nicht lesbar“, kein Absturz des Dienstes.
4. HEIC mit `pillow-heif` auf dem Server (alle Browser, testbar, Metadaten serverseitig kontrolliert), nur nach bestandener Magic-Bytes-Prüfung. Browser-Umwandlung ist verworfen (nur Safari dekodiert HEIC, nicht testbar).
5. Drehung anwenden (`exif_transpose`), dann zwei WebP-Fassungen (480 und 1600 Pixel, Qualität 80) wie in Stufe 1. WebP aus Pillow trägt kein EXIF, XMP oder GPS; ein Test prüft es an einem Foto mit eingebettetem GPS. **Das Original wird nie gespeichert**, auch nicht vorübergehend in der Ablage.
6. Grenzen je Reise: `bilder.max_anzahl` (60, aktive Bilder, besteht) und neu `bilder.max_mb` (Vorgabe 150, Summe der gespeicherten Fassungen) in `reise.yaml`. Beim Überschreiten wird abgelehnt, nichts wird abgeschnitten.
7. Drosselung wie bei Belegen (30 Anfragen je Minute und Person), Zeit- und Größenlimit gegen langsame Uploads.

### Datenformat (P1)

Neue Quelle `eigen` für einen Eintrag in `plan/bilder.yaml`; `urheber` trägt den Anzeigenamen der hochladenden Person, `lizenz` bleibt leer (Verantwortungsangabe statt Lizenz, #613). Neu und **optional**: `besitzer` mit der Konto- oder Personenkennung der hochladenden Person; der Besitznachweis beim Löschen läuft über diese Kennung, nie über den Namen. Alte Einträge ohne `besitzer` bleiben gültig; Quelle `commons` und Altbestand haben keinen Besitzer, ihr Löschen bleibt Sache der Organisator:innen (Zurückziehen wie bisher). Ändert sich das Format doch, bringt der Schritt `neu.py nachziehen` die Umstellung mit Test mit.

Nennung: „Foto: <Name>“ steht an eigenen Fotos (`bauen.py`, bisher kein Eintrag bei `quelle: reise`). Der Name kommt aus dem Konto der hochladenden Person zum Zeitpunkt des Hochladens; wird das Konto gelöscht, ersetzt `namen_ersetzen` ihn durch „gelöschte Person“ (Regel aus #381), die Kennung bleibt als Besitzzuordnung nur für Organisator:innen wirksam.

### Aufräumen verwaister Fassungen (P1, offen aus Stufe 1)

Scheitert das Speichern nach dem Schreiben der Fassungen, bleiben WebP-Dateien ohne Eintrag zurück. Der Vorgang räumt sie im selben Zug auf (Datei ohne Eintrag in `plan/bilder.yaml` unter `medien/bilder/`); ein Test erzwingt den Fehler mitten im Speichern.

### Echtes Löschen (P3)

Dritte, eng begrenzte Ausnahme vom Nur-anhängen (ADR-0009, neben `reise_entfernen` und `namen_ersetzen`): `reisespeicher.bild_entfernen(reise, bid)`. In einer Transaktion (`BEGIN IMMEDIATE`) werden die Inhalte der **zwei festen Pfade** `medien/bilder/<bid>-480.webp` und `medien/bilder/<bid>-1600.webp` in allen Versionen geleert (die Zeile bleibt, `inhalt` und `pruefsumme` werden NULL); danach `_ablage_aufraeumen` (Ablagedatei nur löschen, wenn keine Version irgendeiner Reise mehr auf die Prüfsumme verweist), `verdichten` (VACUUM) und erzwungener Neubau. Kein anderer Pfad, kein Muster, keine andere Tabelle. Das Löschprotokoll erhält den Eintrag, damit das Rückspielen einer alten Sicherung das Bild nicht zurückbringt (Regel aus #381). `pruefen`, `materialisieren` und der Export vertragen geleerte Zeilen. Der Quelltext-Test der Ausnahmen (`test_loeschen_reise.py`, Zeilen um 606) wird um genau diese Funktion erweitert und lässt keine weitere zu.

Zwei identische Uploads teilen einen Blob (inhaltsadressiert). Löscht eine Person ihren Upload, darf der Blob des anderen Uploads bestehen bleiben, solange eine Version ihn braucht; das Aufräumen prüft das. Test mit zwei Bildern gleichen Inhalts.

Recht: die hochladende Person (über `besitzer`) und Organisator:innen. Die Rolle wird über `rolle_aktuell` frisch geprüft. Das Löschen geht nur angemeldet, nie über einen Token.

Verlauf: Der Eintrag „Foto entfernt“ (Datum, wer entfernt hat, Bild-ID) bleibt in `plan/bilder.yaml` mit Status `entfernt`; Datei-Felder, Titel, Bildunterschrift und Alt-Text des Bildes werden geleert, das Bild selbst ist weg. Das ist die Ausnahme zu ADR-0001 Frage 7: IDs und Verlauf bleiben erhalten, nur der Inhalt des Bildes fehlt (Entscheidung 15.11.2026). Die ID `BI-NN` wird nie neu vergeben.

Zusage beim Löschen (folgt der Regel aus #381, `docs/betrieb.md`, Datenschutztabelle, keine neue Produktentscheidung): Sofort aus Seite, Verlauf, Export und Speicher. Sicherungen enthalten das Bild bis zur Rotation, höchstens 30 Tage. Kopien auf Geräten anderer (schon geladen oder offline gespeichert) lassen sich nicht zurückholen; der Text sagt das ehrlich. Der Service Worker nimmt gelöschte Bilder beim nächsten Laden aus dem Cache (Liste der gültigen Bild-Adressen im Precache-Manifest; was nicht mehr darin steht, wird verworfen).

### Link aus dem Chat (P2)

Neues Konnektor-Werkzeug (englischer Name `image_upload_link`, deutscher Alias nach `schnittstelle.py`) gibt einen Hochlade-Link aus. Der Token ist zufällig, in `konten.db` nur als sha256-Hash gespeichert (Muster Anmeldecode und Einladung), gilt **30 Minuten**, erlaubt **höchstens 10 Fotos**, ist **an Reise und Person gebunden** und wird beim Hochladen nicht als Rolle gespeichert: **die Rolle (mindestens mitwirkend) wird bei jedem Hochladen neu geprüft**. Ohne Anmeldung nutzbar, aber nur zum Hochladen (kein Löschen, kein Lesen der Reise). Die Link-Seite hat eine eigene CSP, `Referrer-Policy: no-referrer`, enthält keinen geheimen Seitenlink und lädt keine fremden Ressourcen. Abgelaufene oder verbrauchte Tokens führen zu derselben Ablehnung „Link abgelaufen“. Die Drosselung gilt je Token und je Adresse zusätzlich.

### Doku und Betrieb

- `docs/adr/0009-reisespeicher.md`: dritte Ausnahme, Löschprotokoll; `docs/adr/0001-kern.md`: Verlauf zu Frage 7.
- `docs/konnektor.md`: Werkzeug, Routen. `docs/betrieb.md`: Datenschutztabelle (Löschen eigener Fotos, Sicherungen höchstens 30 Tage, Grenzen). `docs/design.md`: Bausteine; jede Grundform hat weiter genau eine Heimat auf der Seite (ADR-0003).
- Neue Module kommen in die Liste in `betrieb/deploy.sh`. Die neue Fremdbibliothek steht in `THIRD_PARTY.md` mit Lizenz, in `requirements.txt` mit Hashes; `betrieb/veroeffentlichen.sh` prüft vor dem Tausch der venv, dass die Glibc des Servers mindestens 2.28 hat.
- Vor dem Vorspulen laufen die Tests der einbindenden Instanzen mit dem Branch (Anleitung im Reisen-Repo der Instanz), weil Texte, Routen, nginx-Block und Paket betroffen sind.

## Anforderungen

**P1: Hochladen auf der Reiseseite**

- **V1:** Angemeldete Mitglieder ab Rolle mitwirkend können auf der Reiseseite Fotos hinzufügen; Gäste und Nicht-Mitglieder sehen die Funktion nicht und werden vom Dienst abgewiesen. Das Titelbild setzen nur Organisator:innen (bestehende Regel).
- **V2:** Erlaubt sind JPEG, PNG, WebP und HEIC, erkannt an den Magic Bytes; höchstens 12 MB je Datei vor der Verkleinerung.
- **V3:** Das Original wird nie gespeichert. Gespeichert werden zwei WebP-Fassungen ohne EXIF, XMP und GPS, mit angewendeter Drehung.
- **V4:** Je Reise gelten `bilder.max_anzahl` (60) und `bilder.max_mb` (150) aus `reise.yaml`; beim Erreichen wird mit klarer Meldung abgelehnt.
- **V5:** Dekompressionsbomben und defekte Dateien führen zur Ablehnung, nie zum Absturz; `MAX_IMAGE_PIXELS` und Zeitgrenze gelten.
- **V6:** Drosselung wie bei Belegen; Prüfungen von Cookie, Origin und Rolle wie bei `_beleg_hochladen`.
- **V7:** Der Eintrag trägt Quelle `eigen`, Anzeigename der hochladenden Person und die Besitzkennung; die Seite zeigt „Foto: <Name>“.
- **V8:** Vor dem Hochladen steht der Hinweis zu Personen auf Fotos (Wortlaut V17); keine Bestätigung der Urheberschaft wird verlangt.
- **V9:** Gescheiterte Vorgänge hinterlassen keine verwaisten Fassungen; vorhandene Waisen werden beim nächsten Hochladen aufgeräumt.
- **V10:** Beide Beispielreisen: Die Beispielreise (Ida, Karl) nimmt Fotos zusätzlich zu ihren Commons-Bildern an; das Stadtwochenende (Tom, Lea, ohne Bilder) bekommt nur die Möglichkeit zum Hochladen und bleibt sonst unverändert.

**P3: Echtes Löschen**

- **V11:** Die hochladende Person (über die Besitzkennung) und Organisator:innen können ein eigenes Foto löschen; die Rolle wird frisch geprüft, nur angemeldet.
- **V12:** `bild_entfernen` ist die dritte Ausnahme vom Nur-anhängen, begrenzt auf zwei feste Pfade je Bild, in einer Transaktion, mit Aufräumen der Ablage, Verdichten und Neubau; im Löschprotokoll vermerkt.
- **V13:** Im Verlauf bleibt „Foto entfernt“ mit Datum und wer entfernt hat, ohne Bild; die ID wird nie neu vergeben.
- **V14:** Die Zusage beim Löschen (Wortlaut V17) entspricht der Regel aus #381: sofort aus Seite, Verlauf, Export und Speicher; Sicherungen bis zur Rotation, höchstens 30 Tage; Kopien auf fremden Geräten nicht zurückholbar.
- **V15:** Der Service Worker nimmt gelöschte Bilder beim nächsten Laden aus dem Cache.

**P2: Link aus dem Chat**

- **V16:** Das Konnektor-Werkzeug gibt einen Hochlade-Link aus: 30 Minuten gültig, höchstens 10 Fotos, an Reise und Person gebunden, Token nur als Hash in `konten.db`, Rolle beim Hochladen neu geprüft; ohne Anmeldung nur Hochladen; Link-Seite mit eigener CSP, `Referrer-Policy: no-referrer`, ohne geheimen Seitenlink.

**Übergreifend**

- **V17:** Wortlaut und Gestaltung der neuen Oberfläche (Hochladen, Hinweis, Löschen mit Zusage, „Foto: <Name>“, Link-Seite, Ablehnungen) folgen dem vom Product Owner freigegebenen Entwurf (Claude-Artefakt, #436, vor dem Bauen gezeigt und inhaltlich ins Issue #582 übertragen). Die folgende Tabelle ist der vorgeschlagene Wortlaut und wird bei Änderungen im Entwurf hier nachgeführt. Alle Texte stehen in `engine/texte_<sprache>.py` in allen Sprachen, nie im Code.
- **V18:** Format von `plan/bilder.yaml`: neue Felder optional, alte Einträge gültig; bei einer Formatänderung bringt `neu.py nachziehen` die Umstellung mit Test mit.
- **V19:** Neue Module stehen in der Liste in `betrieb/deploy.sh`; `pillow-heif` steht in `THIRD_PARTY.md` und mit Hashes in `requirements.txt`; das Veröffentlichen prüft die Glibc.
- **V20:** Doku nachgeführt: ADR-0009, ADR-0001 (Verlauf zu Frage 7), `docs/konnektor.md`, `docs/betrieb.md`, `docs/design.md`.

### Vorgeschlagener Wortlaut (Deutsch, zur Freigabe im Entwurf)

Entwurf der Oberfläche (#436): privates Claude-Artefakt „#582 Eigene Fotos – Entwurf“ mit acht Ansichten (Ortsseite mit „+ Foto hinzufügen“, Blatt nach der Fotoauswahl, Großansicht eines eigenen Fotos, Bestätigung „Foto entfernen?“, Stadtwochenende ohne Bilder, Link im Chat, Seite hinter dem Link, abgelaufener Link mit Meldungen). Bildunterschriften werden beim Hochladen nicht abgefragt, sondern später im Chat ergänzt. Der Inhalt des Entwurfs wird nach der Freigabe als Kommentar ins Issue #582 übertragen.

| Stelle | Wortlaut |
|---|---|
| Knopf Hochladen (unter den Bildern eines Dings, auch ohne Bilder) | „+ Foto hinzufügen“; danach Blatt „<n> Fotos zu <Ding>“ mit Knöpfen „Abbrechen“ und „<n> Fotos hochladen“; nicht angemeldet: „Anmelden, um Fotos hinzuzufügen.“ |
| Hinweis zu Personen auf Fotos (vor dem Hochladen, ohne Haken; Seite und Link-Seite) | „Denk an die Menschen auf den Fotos. Diese Seite kann jede Person lesen, die den Link kennt, auch ohne Anmeldung. Lade nur Fotos hoch, auf denen du selbst bist oder auf denen andere damit einverstanden sind. Für das, was du hochlädst, bist du verantwortlich.“ Darunter klein: „Standort und Kameradaten nimmt Frieda vor dem Speichern aus dem Foto heraus.“ |
| Nennung am Foto | „Foto: <Name>“ |
| Zusage beim Löschen (vor dem Bestätigen) | „Das Foto wird sofort von der Seite, aus dem Verlauf, aus dem Export und aus dem Speicher entfernt. In Sicherungen bleibt es noch bis zu 30 Tage, danach ist es auch dort weg. Wer das Foto schon geladen oder offline gespeichert hat, behält diese Kopie; die kann Frieda nicht zurückholen. Im Verlauf steht danach nur noch: ‚Foto entfernt am <Datum> von <Name>‘.“ Überschrift „Foto entfernen?“, Knöpfe „Behalten“ und „Entfernen“ |
| Knopf Löschen | „Foto entfernen“ |
| Verlaufseintrag | „Foto entfernt am <Datum> von <Name>“ |
| Link-Seite, Überschrift | „Fotos für „<Reise>“ hochladen“, darunter „zu <Ding> · als <Name>“, Knopf „Fotos auswählen“, je Foto „✓ hochgeladen“ oder „wird hochgeladen …“, unten „Noch <m> Minuten · noch <k> von 10 Fotos.“ |
| Link-Seite, Erklärung | „Dieser Link gilt 30 Minuten und für bis zu 10 Fotos. Teile ihn nicht. Du kannst hier nur hochladen, nichts ansehen oder löschen.“ |
| Ablehnung zu groß | „Dieses Foto ist größer als 12 MB. Verkleinere es oder wähle ein anderes.“ |
| Ablehnung falsches Format | „Dieses Format kann Frieda nicht lesen. Erlaubt sind JPEG, PNG, WebP und HEIC.“ |
| Ablehnung Grenze erreicht | „Diese Reise hat die Grenze für Fotos erreicht (<Anzahl> Fotos oder <MB> MB). Entferne ein Foto oder sprich mit einer Organisator:in.“ |
| Ablehnung Link abgelaufen (eigene Seite, Überschrift „Link abgelaufen“) | „Dieser Link ist abgelaufen oder aufgebraucht. Bitte Frieda im Chat um einen neuen.“ |
| Ablehnung zu viele Anfragen | „Zu viele Versuche. Bitte warte kurz und versuche es dann noch einmal.“ |

## Test Plan

### Automated Tests (TDD RED)

Je Fall ein Test, zuerst der Test, dann der Code. Erfundene Konten und Reisen; beide Beispielreisen. Hauptdatei `engine/tests/test_bilder_eigen.py`.

**P1**

- [ ] GIVEN ein JPEG mit eingebettetem GPS und Kameradaten WHEN hochgeladen THEN enthalten beide WebP-Fassungen weder EXIF noch XMP noch GPS, und das Original liegt nirgends im Speicher oder in der Ablage.
- [ ] GIVEN ein JPEG mit Drehung 90 Grad in den Metadaten WHEN hochgeladen THEN ist die Fassung gedreht und trägt keine Drehangabe.
- [ ] GIVEN ein HEIC-Foto (kleines erfundenes Testbild) WHEN hochgeladen THEN entstehen zwei WebP-Fassungen; GIVEN ein HEIC mit falschen Magic Bytes THEN Ablehnung.
- [ ] GIVEN eine Datei über 12 MB WHEN hochgeladen THEN Ablehnung „zu groß“ am Rückmeldedienst, ohne den Schreibweg zu erreichen.
- [ ] GIVEN eine Textdatei mit Endung `.jpg` WHEN hochgeladen THEN Ablehnung „falsches Format“ (Magic Bytes entscheiden).
- [ ] GIVEN ein Bild mit mehr Pixeln als `MAX_IMAGE_PIXELS` WHEN hochgeladen THEN Ablehnung ohne Absturz des Dienstes.
- [ ] GIVEN eine Reise mit 60 aktiven Bildern, oder mit Fassungen über `bilder.max_mb` WHEN ein weiteres Foto kommt THEN Ablehnung „Grenze erreicht“; nichts wird gespeichert.
- [ ] GIVEN mehr als 30 Uploads in einer Minute von einer Person WHEN weitere kommen THEN Ablehnung „zu viele Anfragen“.
- [ ] GIVEN Rollen gast, mitwirkend, organisator, Nicht-Mitglied, keine Anmeldung, falscher Origin WHEN hochgeladen THEN nur mitwirkend und organisator werden angenommen; alle anderen bekommen die passende Ablehnung.
- [ ] GIVEN eine Rolle, die im veröffentlichten Stand hinterherhinkt WHEN hochgeladen THEN entscheidet `rolle_aktuell`.
- [ ] GIVEN ein erfolgreicher Upload THEN trägt der Eintrag Quelle `eigen`, Anzeigename, Besitzkennung; die gebaute Seite zeigt „Foto: <Name>“; der Schreibweg nimmt die Upload-Route nur mit `X-Frieda-Dienst`.
- [ ] GIVEN ein Fehler mitten im Speichern WHEN der Vorgang endet THEN bleiben keine verwaisten Fassungen; vorhandene Waisen werden beim nächsten Hochladen aufgeräumt.
- [ ] GIVEN ein alter Eintrag ohne `besitzer` THEN bleibt er gültig und `neu.py nachziehen` ändert nichts.
- [ ] GIVEN das Stadtwochenende (ohne Bilder) THEN zeigt die Seite die Möglichkeit zum Hochladen, sonst unverändert, keine Fehler; die Beispielreise zeigt Commons-Bilder und eigene Fotos nebeneinander.
- [ ] GIVEN `nginx-reise.conf` THEN gibt es einen Block für Foto-Uploads mit `client_max_body_size` zwischen 12m und 14m, der übrige Ort bleibt unverändert (`test_betrieb.py`).
- [ ] GIVEN `betrieb/deploy.sh` THEN enthält die Modulliste jedes neue Modul (bestehender Test).
- [ ] GIVEN `THIRD_PARTY.md` und `requirements.txt` THEN stehen `pillow-heif` mit Lizenz und Hashes darin; die Glibc-Prüfung steht im Veröffentlichen.
- [ ] AC-9, ohne Handschritt (`test_betrieb.py`): GIVEN eine Instanz mit alter venv und alter nginx-Vorlage WHEN `betrieb/veroeffentlichen.sh` im Testlauf (Probe-Instanz wie die bestehenden Veröffentlichen-Tests) läuft THEN baut es die venv wegen der geänderten `requirements.txt` neu, `import pillow_heif` gelingt darin, der Foto-Block der nginx-Vorlage wird installiert, und es gibt keinen Abbruch, der einen Handschritt verlangt; bei Glibc unter 2.28 bricht es vor dem Tausch der venv mit klarer Meldung ab und die alte venv bleibt.
- [ ] Browsertest (Chromium und WebKit, erster mit echtem `setInputFiles`): GIVEN angemeldet mit Rolle mitwirkend WHEN ein Foto gewählt wird THEN zeigt die Seite zuerst den Hinweis, dann das Foto mit „Foto: <Name>“; bei 360 px keine Überbreite.

**P3**

- [ ] GIVEN die hochladende Person WHEN sie ihr Foto entfernt THEN sind beide Fassungen aus Seite, `daten.json`, Export, allen Versionen und der Ablage verschwunden; der Verlaufseintrag „Foto entfernt“ bleibt.
- [ ] GIVEN eine Organisator:in WHEN sie ein fremdes eigenes Foto entfernt THEN gilt dasselbe; GIVEN eine mitwirkende andere Person THEN Ablehnung.
- [ ] GIVEN zwei Uploads mit identischem Inhalt WHEN einer gelöscht wird THEN bleibt der Blob des anderen lesbar, und `pruefen()` ist grün; wird auch der zweite gelöscht, ist die Ablagedatei weg.
- [ ] GIVEN `bild_entfernen` THEN berührt sie nur die zwei festen Pfade des Bildes und keine andere Zeile; ein Test mit Pfaden anderer Bilder und Reisen belegt es.
- [ ] GIVEN der Quelltext THEN lässt der Ausnahmen-Test (`test_loeschen_reise.py`) genau `reise_entfernen`, `namen_ersetzen` und `bild_entfernen` zu; ADR-0009 nennt alle drei.
- [ ] GIVEN eine alte Sicherung wird zurückgespielt THEN entfernt der tägliche Lauf das Bild über das Löschprotokoll erneut.
- [ ] AC-14, Browsertest (Chromium und WebKit): GIVEN angemeldet als hochladende Person in der Großansicht ihres Fotos WHEN „Foto entfernen“ gedrückt wird THEN erscheint der Dialog „Foto entfernen?“ mit dem Wortlaut aus `texte_de.py` (sofort entfernt, Sicherungen bis zu 30 Tage, fremde Kopien nicht zurückholbar, Verlaufseintrag) und den Knöpfen „Behalten“ und „Entfernen“; „Behalten“ lässt das Foto unverändert, erst „Entfernen“ sendet die Anfrage; GIVEN eine andere mitwirkende Person THEN gibt es den Knopf nicht; ein Texttest prüft, dass der Schlüssel der Zusage in allen Sprachen die Zahl 30 trägt.
- [ ] GIVEN der Service Worker mit einem gelöschten Bild im Cache WHEN die Seite neu lädt THEN ist das Bild aus dem Cache entfernt (Browsertest, Chromium und WebKit).
- [ ] GIVEN eine Reise nach Konto-Löschung der hochladenden Person THEN steht „gelöschte Person“ in der Nennung (`namen_ersetzen`), das Foto bleibt, Organisator:innen können löschen.
- [ ] GIVEN `docs/betrieb.md` THEN nennt die Datenschutztabelle das Löschen eigener Fotos mit Zusage und höchstens 30 Tagen für Sicherungen.

**P2**

- [ ] GIVEN eine Person ab mitwirkend WHEN sie das Werkzeug aufruft THEN kommt ein Link; in `konten.db` steht nur der Hash, nie der Token.
- [ ] GIVEN ein Token WHEN er 31 Minuten alt ist, 10 Fotos hochgeladen wurden, die Reise oder die Person nicht passt THEN Ablehnung „Link abgelaufen“ in allen Fällen mit derselben Antwort.
- [ ] GIVEN eine inzwischen herabgestufte Rolle (gast) WHEN mit gültigem Token hochgeladen wird THEN Ablehnung (Rolle neu geprüft).
- [ ] GIVEN ein Token WHEN Löschen, Lesen der Reise oder ein anderer Ort aufgerufen wird THEN abgewiesen (nur Hochladen).
- [ ] GIVEN die Link-Seite THEN trägt sie eigene CSP und `Referrer-Policy: no-referrer`, enthält keine Adresse der Reiseseite und lädt keine fremde Ressource.
- [ ] GIVEN `docs/konnektor.md` und `schnittstelle.py` THEN stehen Werkzeug, englischer Name und deutscher Alias darin (bestehende Doku-Tests).
- [ ] GIVEN ein Konto wird gelöscht THEN sind seine Tokens in `konten.db` entfernt.

**Übergreifend**

- [ ] `test_texte.py`: alle neuen Schlüssel in allen Sprachen, die Ausnahmelisten werden nicht länger.
- [ ] Altbestand bleibt grün: `test_bilder.py`, `test_bilder_konto.py`, `test_rueckmeldungen.py`, `test_loeschen_reise.py`, `test_export.py`, `test_sicherheit.py`, `test_design.py`.
- [ ] Vor dem Vorspulen laufen die Tests der einbindenden Instanz mit dem Branch.

## Acceptance Criteria

**P1**

- **AC-1 (V1, V6):** Given eine angemeldete Person mit Rolle mitwirkend oder organisator / When sie auf der Reiseseite ein Foto wählt / Then wird es angenommen; Given Gast, Nicht-Mitglied, keine Anmeldung oder fremder Origin / Then wird es abgelehnt, und die Rolle wird über `rolle_aktuell` frisch geprüft.
- **AC-2 (V2, V5):** Given JPEG, PNG, WebP oder HEIC bis 12 MB / When hochgeladen / Then wird es angenommen; Given eine größere, falsche, beschädigte oder zu pixelreiche Datei / Then kommt die passende Ablehnung (V17), der Dienst bleibt stabil.
- **AC-3 (V3):** Given ein Foto mit GPS und Kameradaten / When es gespeichert ist / Then enthalten die Fassungen keine Metadaten, die Drehung ist angewendet und das Original ist nirgends gespeichert.
- **AC-4 (V4):** Given eine Reise an `bilder.max_anzahl` oder `bilder.max_mb` / When ein weiteres Foto kommt / Then wird mit „Grenze erreicht“ abgelehnt, und `bilder.max_mb` ist in `reise.yaml` einstellbar (Vorgabe 150).
- **AC-5 (V7):** Given ein gespeichertes eigenes Foto / When die Seite gebaut wird / Then steht der Eintrag mit Quelle `eigen`, Besitzkennung und der Nennung „Foto: <Name>“.
- **AC-6 (V8):** Given jemand will ein Foto hinzufügen / When das Formular erscheint / Then steht der Hinweis zu Personen auf Fotos vorher da, ohne Haken und ohne Frage nach der Urheberschaft.
- **AC-7 (V9):** Given ein gescheitertes Speichern / When der Vorgang endet / Then bleiben keine verwaisten Fassungen zurück; vorhandene Waisen verschwinden beim nächsten Hochladen.
- **AC-8 (V10, V18):** Given die Beispielreise und das Stadtwochenende / When Fotos hochgeladen werden und die Seiten gebaut sind / Then funktionieren beide fehlerfrei, und alte Einträge in `plan/bilder.yaml` bleiben gültig.
- **AC-9 (V19):** Given `pillow-heif` und der Foto-Block in nginx / When das Veröffentlichen läuft / Then sind Bibliothek (Lizenz, Hashes), Glibc-Prüfung, Deploy-Liste und der nginx-Block ohne Handschritt vorhanden.

**P3**

- **AC-10 (V11):** Given ein eigenes Foto / When die hochladende Person oder eine Organisator:in es entfernt / Then geschieht es; Given eine andere mitwirkende Person oder ein Token / Then wird es abgelehnt.
- **AC-11 (V12):** Given das Löschen / When `bild_entfernen` läuft / Then sind beide Fassungen in allen Versionen, in der Ablage, im Export und auf der Seite weg, nur die zwei Pfade des Bildes sind betroffen, das Löschprotokoll hat den Eintrag, `pruefen()` ist grün.
- **AC-12 (V12):** Given zwei Uploads mit gleichem Inhalt / When einer gelöscht wird / Then bleibt der andere unversehrt.
- **AC-13 (V13):** Given ein entferntes Foto / When der Verlauf gelesen wird / Then steht „Foto entfernt“ mit Datum und Person ohne Bild, die ID wird nie neu vergeben.
- **AC-14 (V14):** Given der Dialog zum Löschen / When er erscheint / Then enthält er die Zusage nach der Regel aus #381: sofort entfernt, Sicherungen höchstens 30 Tage, fremde Kopien nicht zurückholbar.
- **AC-15 (V15):** Given ein gelöschtes Bild im Cache eines Geräts / When die Seite wieder geladen wird / Then ist es aus dem Cache entfernt.

**P2**

- **AC-16 (V16):** Given eine Person ab mitwirkend / When Frieda das Werkzeug ausführt / Then kommt ein Link, der 30 Minuten gilt, höchstens 10 Fotos erlaubt, an Reise und Person gebunden ist und in `konten.db` nur als Hash steht.
- **AC-17 (V16):** Given ein Token mit abgelaufener Zeit, erschöpftem Zähler, falscher Reise oder Person / When hochgeladen wird / Then kommt immer dieselbe Ablehnung „Link abgelaufen“.
- **AC-18 (V16):** Given ein gültiger Token, aber inzwischen herabgestufte Rolle / When hochgeladen wird / Then wird abgelehnt.
- **AC-19 (V16):** Given ein Token / When etwas anderes als Hochladen versucht wird (Löschen, Lesen) / Then wird es abgewiesen.
- **AC-20 (V16):** Given die Link-Seite / When sie geladen wird / Then trägt sie eigene CSP und `Referrer-Policy: no-referrer`, enthält keinen geheimen Seitenlink und lädt keine fremden Ressourcen.
- **AC-21 (V16):** Given ein gelöschtes Konto / When aufgeräumt wird / Then sind seine Tokens entfernt.

**Übergreifend**

- **AC-22 (V17):** Given die Spec-Freigabe / When gebaut wird / Then folgen Wortlaut und Gestaltung dem freigegebenen Entwurf; die Tabelle V17 stimmt mit `texte_de.py` überein, alle Sprachen sind vollständig (`test_texte.py`).
- **AC-23 (V20):** Given die Pakete sind ausgeliefert / When die Doku geprüft wird / Then sind ADR-0009 (dritte Ausnahme), ADR-0001 (Verlauf zu Frage 7), `docs/konnektor.md`, `docs/betrieb.md` und `docs/design.md` nachgeführt.
- **AC-24:** Given die Pakete / When vor dem Vorspulen die Tests der einbindenden Instanz mit dem Branch laufen / Then sind sie grün; die volle Testsuite ist ohne echte Reisen grün.

## Definition of Done

- [ ] Spec und Entwurf (#436) sind vom Product Owner freigegeben; der Entwurf steht inhaltlich im Issue #582.
- [ ] AC-1 bis AC-24 sind erfüllt und durch Tests belegt, zuerst die Tests (RED), dann der Code (GREEN).
- [ ] P1 und P3 sind gemeinsam ausgeliefert; P2 folgt oder liefert zusammen.
- [ ] Die Tests der einbindenden Instanz laufen mit dem Branch grün.
- [ ] Auf dem Server der Instanz aktiv: neue venv mit `pillow-heif`, nginx-Block, ohne Handschritt.
- [ ] #582 ist erst geschlossen, wenn alles end-to-end erledigt ist.

## Prüfstelle ADR-0001 (zehn Fragen)

1. **Ontologie statt Sonderfall:** ja. Das Foto ist ein Bild als Eigenschaft der Grundformen (eigene Liste wie in Stufe 1); durchgespielt an Wanderung (mit Bildern) und Stadtwochenende (ohne).
2. **Kein Katalog:** ja. Keine Art, kein Merkmal, keine reisespezifische Regel in der Engine; Grenzen stehen in `reise.yaml`.
3. **Keine KI in Frieda:** ja. Reine Umwandlung und Zugriffsregel; keine Bilderkennung, keine Gesichtserkennung.
4. **Die Tür:** neues Werkzeug `image_upload_link` (englischer Name, deutscher Alias); Frieda lädt selbst nichts hoch, sie gibt nur den Link aus. Bestehende Werkzeuge unverändert.
5. **Herkunft:** eigene Fotos tragen Quelle `eigen`, Name der hochladenden Person und Besitzkennung; „Foto: <Name>“ steht sichtbar am Bild; die Verantwortung liegt bei der hochladenden Person (Entscheidung 17.11.2026).
6. **Rollen entscheiden:** Hinzufügen ab mitwirkend, Titelbild nur organisator, Löschen durch Besitz oder organisator; die Rolle wird bei jeder Handlung frisch geprüft, auch beim Hochladen mit Token.
7. **IDs und Verlauf:** `BI-NN` wird nie neu vergeben. **Ausnahme (Entscheidung 15.11.2026):** Beim echten Löschen bleibt der Verlaufseintrag „Foto entfernt“ ohne Bild; Inhalt der Bilddateien und Bildtexte werden wirklich entfernt. Eintrag im Verlauf von ADR-0001 mit diesem Paket; Ausnahme in ADR-0009 auf zwei feste Pfade je Bild begrenzt.
8. **PWA:** Der Service Worker nimmt gelöschte Bilder aus dem Cache; Offline-Verhalten und `offline_mb` bleiben (Warnung beim Bau gilt auch für eigene Fotos).
9. **Claude Code:** Reiseinhalte entstehen weiter im AI-Client; Fotos kommen von Mitwirkenden über Seite oder Link, nicht über Claude Code.
10. **Dokumentation:** ADR-0009, ADR-0001, `docs/konnektor.md`, `docs/betrieb.md`, `docs/design.md` (siehe V20).

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine neue Nummer; Ergänzung von ADR-0009 (dritte Ausnahme `bild_entfernen`) und Verlauf in ADR-0001 (Frage 7), beides mit P3.
- **Rationale:** Echtes Löschen widerspricht dem Nur-anhängen des Reisespeichers und braucht eine ausdrückliche, eng begrenzte Ausnahme (zwei feste Pfade, eine Transaktion, Löschprotokoll), wie bei `reise_entfernen` und `namen_ersetzen`. Der Weg der Bytes bleibt innerhalb der bestehenden Dienstgrenze (`X-Frieda-Dienst`, keine Pfadübergabe). Eine eigene ADR-Nummer lohnt nicht, weil die Entscheidung den Rahmen von ADR-0009 nur präzisiert.

## Risiken

| Risiko | Gegenmaßnahme |
|---|---|
| Echtes Löschen gegen Nur-anhängen (ADR-0009) | dritte, eng begrenzte Ausnahme mit Quelltext-Test, Löschprotokoll, Test mit fremden Pfaden |
| Kopien außerhalb des Speichers (Sicherung, Geräte, Caches) | ehrliche Zusage (höchstens 30 Tage Sicherung, Geräte nicht zurückholbar), Service-Worker-Bereinigung, Löschprotokoll gegen Rückspielen |
| Dekompressionsbomben und Fehler im HEIC-Dekoder | `MAX_IMAGE_PIXELS`, Zeitgrenze, Magic Bytes vorab, begrenzter Unterprozess |
| Weitergeleiteter Link aus dem Chat | 30 Minuten, höchstens 10 Fotos, Bindung an Person, Rolle neu geprüft, nur Hochladen, Hash in der Datenbank, `no-referrer` |
| Zwei identische Uploads teilen einen Blob | Aufräumen prüft Verweise aller Versionen; Test |
| Langsame Uploads binden den Rückmeldedienst | Zeit- und Größenlimit, Drosselung, getrennter nginx-Block |
| Neue Fremdbibliothek (libheif, LGPL) | Lizenz in `THIRD_PARTY.md`, Hashes, Glibc-Prüfung vor dem Tausch der venv; auf dem Server testen, dass das Rad existiert |
| Personen auf Fotos ohne Einwilligung | Hinweis vor dem Hochladen, Verantwortung bei der hochladenden Person, echtes Löschen als Rückweg |
| Verwaiste Fassungen nach gescheitertem Speichern | Aufräumen im selben Zug, Test mit erzwungenem Fehler |
| Instanzen nutzen Texte, Routen, nginx | Tests der einbindenden Instanz vor dem Vorspulen |
| Hochladen ohne Löschen im Betrieb | P1 geht nur zusammen mit P3 live |

## Known Limitations

- Kopien, die andere schon heruntergeladen oder offline gespeichert haben, lassen sich nicht zurückholen; Sicherungen halten das Bild bis zur Rotation, höchstens 30 Tage.
- Für Fotos wird keine Urheberschaft geprüft (Entscheidung 17.11.2026).
- Commons-Bilder und Altbestand haben keinen Besitzer; ihr Zurückziehen bleibt wie in Stufe 1.
- Die Seite ist per geheimem Link lesbar; der Hinweis zu Personen kann nur mahnen, nicht verhindern.

## Changelog

- 2026-11-21: Erste Fassung der Spec zu Stufe 2 (#582), drei Pakete P1, P3, P2 mit Bau-Reihenfolge P1, P3, P2; Wortlaut-Vorschlag als Tabelle zur Freigabe zusammen mit dem Entwurf (#436).
