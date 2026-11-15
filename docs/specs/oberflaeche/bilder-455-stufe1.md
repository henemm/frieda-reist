---
entity_id: bilder-455-stufe1
type: feature
created: 2026-11-15
updated: 2026-11-15
status: draft
version: "1.0"
tags: [bilder, commons, lizenz, titelbild, grossansicht, offline, konnektor, sicherheit, meine-reisen]
---

# Bilder Stufe 1: Bilder aus Wikimedia Commons als eigener Teil der Reise, mit Herkunft, Lizenz und Darstellung (#455, #581)

## Approval

- [ ] Approved

## Purpose

Reisen haben heute keine Bilder mit Herkunft: Fotos stehen als lose Dateien im Text, und Bilder von fremden Adressen werden beim Bau
ungeprüft durchgelassen (#581, Sicherheitslücke). Stufe 1 macht das Bild zu einem eigenen Teil der Reise mit Kennung `BI-NN`, genau
einer Zuordnung und lückenloser Herkunft. Claude nennt über den Konnektor nur eine Commons-Datei oder eine Wikidata-Kennung; Frieda
holt das Bild selbst, prüft die Lizenz deterministisch gegen eine Positivliste, legt zwei Fassungen ab und zeigt es nach dem
freigegebenen Entwurf (Product Owner, 15.11.2026, Variante A) mit Namensnennung. Fremde Bildadressen im Text werden gesperrt.
Eigene Fotos und echtes Löschen sind Stufe 2 (#582) und nicht Teil dieser Spec.

## Source

- **Files:** neu `engine/bilder.py` (Liste, Abruf, Lizenzregel, Fassungen); geändert `engine/reisespeicher.py` (nur falls Export
  oder Löschen die neuen Dateien nicht schon mitnehmen), `engine/neu.py`, `engine/routen.py`,
  `engine/schreiben.py`, `engine/reise.py`, `engine/konnektor.py`, `engine/schnittstelle.py`, `engine/bauen.py`,
  `engine/vorlage.html`, `engine/sw.vorlage.js`, `engine/anmeldung.py`, `engine/texte_de.py`, `engine/texte_en.py` und alle weiteren
  `engine/texte_<kürzel>.py`, `betrieb/deploy.sh`, Beispielreise, `THIRD_PARTY.md`, `docs/konnektor.md`, `docs/design.md`,
  `docs/ontologie.md`, Verlauf in `docs/adr/0001-kern.md`.
- **Kontext und Analyse:** `docs/context/bilder-455-stufe1.md` (verbindlich).
- **Kern (ADR-0001):** Ein Bild ist keine Grundform, keine Art und kein Merkmal, sondern eine Eigenschaft der Grundformen mit eigener
  Liste (wie die Packliste). Die Lizenzregel prüft Frieda; Claude wählt nur aus.

## Dependencies

| Abhängigkeit | Art | Bedeutung |
|---|---|---|
| #455 Abschnitte 4–9, Freigabe 15.11.2026 | Anforderung | Weg A, Darstellung (Variante A), Rechte, Offline |
| #581 | Anforderung | Hotlink-Sperre und CSP, Teil von P1 |
| #582 | Folgearbeit | eigene Fotos, echtes Löschen (Stufe 2), nicht hier |
| ADR-0001, ADR-0002, ADR-0003 | Regel | Bild als Eigenschaft der Grundformen, Bausteine, Heimat |
| `engine/reisespeicher.py` (Ablage) | intern | Bilddateien als ausgelagerte Medien, Export, Löschen der Reise |
| `engine/instanz.py` (`kennung()`) | intern | User-Agent für Commons und Wikidata |
| Pillow | Bibliothek | Inhaltsprüfung, WebP-Fassungen; schon in `engine/requirements.txt` und `THIRD_PARTY.md`, kein neuer Fremdbestandteil |
| Wikimedia Commons API, Wikidata | extern | Metadaten und Bild; in Tests nur als Fixtures |
| Tests der einbindenden Instanz | Betrieb | vor dem Vorspulen jedes Pakets mit dem Branch |

## Scope

| Paket | Dateien (Auswahl) | Geschätzte Änderung |
|---|---|---|
| P1 | neu `engine/bilder.py`, `engine/tests/test_bilder.py` mit Fixtures; `neu.py`, `routen.py`, `schreiben.py`, `reise.py`, `konnektor.py`, `schnittstelle.py`, `bauen.py` (Sperre, CSP), `texte_*.py`, `betrieb/deploy.sh`, `docs/konnektor.md` (Werkzeugliste), `engine/reisespeicher.py` (Prüfung Export/Löschen),
Beispielreise, `THIRD_PARTY.md`, `test_sicherheit.py`, Seitentest Karte unter CSP, `test_design.py`, `test_betrieb.py` | +1500 bis +1800 Zeilen |
| P2 | `bauen.py`, `vorlage.html`, `sw.vorlage.js`, `texte_*.py`, `docs/design.md`, `test_pwa.py`, neue Seitentests | +1500 bis +2000 Zeilen, überwiegend Vorlage |
| P3 | `anmeldung.py`, `konnektor.py` (Route `/bild/…`), `texte_*.py`, `docs/konnektor.md` (Route), `docs/ontologie.md`, ADR-0001-Verlauf, Tests | +300 bis +500 Zeilen |

## Pakete

Drei Pakete, je ein eigener PR, in dieser Reihenfolge, je für sich lieferbar. Jede Regel und jedes Kriterium trägt sein Paket (P1, P2,
P3). Vor dem Vorspulen jedes Pakets laufen die Tests der einbindenden Instanz mit dem Branch (neue Meldungstexte und Datenformat).

- **P1 Daten, Werkzeug, Sperre, nachziehen:** Liste `plan/bilder.yaml`, Kennung `BI-`, Rechte, Abruf, Lizenzregel, Fassungen in der
  Ablage, Werkzeuge mit ihrem Eintrag in `docs/konnektor.md`, Hotlink-Sperre (#581) und `bilder_nachziehen`. Der Bau zeigt in P1
  nur Bilder, die im Text mit `![…](BI-NN)` stehen (V10a); Titelbild, Kopfbilder und Großansicht kommen erst mit P2.
- **P2 Bau, Darstellung, Service Worker:** Daten an die Vorlage, alle Bausteine nach dem freigegebenen Entwurf, Offline.
- **P3 „Meine Reisen“ und Doku:** Kachel mit Titelbild über eine angemeldete Route, Dokumentation.

## Verhalten

### Datenformat (P1)

**V1 (P1) Liste.** Jede Reise kann `plan/bilder.yaml` haben, Kennung `BI-NN`. `BI-` kollidiert nicht mit der Buchung `B-`: Es wird
in `neu.ARTEN`, `routen.MUSTER` und `schreiben.ID_MUSTER` ergänzt, und die Erkennung von `B-nn` trifft `BI-03` nicht (und umgekehrt).
Felder je Bild:

- `id`; `zu` (genau eine ID einer Grundform, oder `reise` für das Titelbild-Umfeld);
- `quelle`: `commons: <Dateiname>`, `wikidata: Q…` zusammen mit dem aufgelösten Dateinamen, oder `reise` für übernommenen Altbestand;
- `urheber` (gesäuberter Text), `lizenz` (Kurzname), `lizenz_url`, `seite` (Commons-Seite); bei `quelle: reise` entfallen diese vier;
- `bildunterschrift` und `alt` (beide freiwillig, von Claude);
- `titelbild` (Wahrheitswert, höchstens eines je Reise);
- `status`: `aktiv` oder `zurueckgezogen`;
- `dateien`: `klein` (480 px breit, WebP) und `gross` (1600 px breit, WebP) unter `medien/bilder/`; `breite`, `hoehe`;
- `hinzugefuegt`: Datum und Person.

**V2 (P1) Zurückziehen statt Löschen.** Ein zurückgezogenes Bild wird nirgends mehr gezeigt (weder Seite noch Kachel noch
Offline-Liste), bleibt aber in Liste und Ablage und lässt sich wiederherstellen. Echtes Löschen gibt es erst in Stufe 2 (#582).

**V3 (P1) Grenzen je Reise.** Höchstens 60 aktive Bilder; das 61. wird beim Anlegen mit Katalogtext abgelehnt. (P2) Die
Offline-Grenze beträgt 25 MB (Summe der Offline-Dateien nach V20); der Bau warnt bei Überschreitung und bricht nicht ab. `max_anzahl` (P1) und `offline_mb` (P2) stehen in
`reise.yaml` unter `bilder: {max_anzahl: 60, offline_mb: 25}` und sind dort änderbar (Organisator:innen).

### Werkzeuge und Rechte (P1)

**V4 (P1) `image_add` (Alias `bild_hinzufuegen`).** Parameter: `commons` (Dateiname) ODER `wikidata` (Q-Kennung, gelesen wird P18),
`zu` (Pflicht), freiwillig `bildunterschrift`, `alt` und `titelbild` (nur Organisator:innen, V6). Genau eine der beiden Quellen,
sonst Ablehnung. Parameternamen im Schema englisch, intern deutsch (`schnittstelle.PARAMETER`): `zu` → `belongs_to`,
`bildunterschrift` → `caption`, `alt` → `alt_text`, `titelbild` → `title_image`, `zurueckziehen` → `withdraw`, `wiederherstellen` →
`restore`; `commons` und `wikidata` gleich. Das Bild wird nie als
Daten durchs Gespräch gereicht (64-KB-Grenze), nur Name oder Kennung. Die Antwort an Claude enthält eine kleine Vorschau (`MitBild`)
zur Kontrolle sowie Urheber und Lizenz.

**V5 (P1) `image_update` (Alias `bild_aendern`).** Ändert `bildunterschrift`, `alt`, `zu`, setzt `zurueckziehen` oder stellt wieder
her, setzt `titelbild`. Ein neues Titelbild löst das bisherige ab. `zu` darf nur auf eine vorhandene ID oder auf `reise` zeigen.

**V6 (P1) Rechte.** In `reise.AKTIONEN`: Bild hinzufügen, ändern, zurückziehen und wiederherstellen ab `mitwirkend`; Titelbild setzen nur `organisator`. Die
Werkzeuge stehen in allen drei Registern (`konnektor`, `schnittstelle` mit deutschem Alias, `schreiben.WERKZEUGE`).

### Abruf und Lizenz (P1)

**V7 (P1) Abruf.** Commons-API `imageinfo` mit `extmetadata` und `iiurlwidth=1600` (nie das Original), bei Wikidata zuerst P18.
User-Agent aus `instanz.kennung()`, Zeitlimit 20 s je Anfrage, eine Wiederholung bei 429 und 5xx, Anfragen nacheinander,
Metadaten-Antwort höchstens 1 MB, Bilddatei höchstens 15 MB. Der Abruf läuft vor der Schreibsperre (Muster `kartenpunkte_vorab`); unter der Sperre wird nicht auf das Netz gewartet.
Eine Datei über 15 MB vor der Verkleinerung wird abgelehnt (Grenze wie bei Belegen). Pillow prüft den Inhalt; angenommen werden nur Rasterbilder (kein SVG, Video, PDF). Beide WebP-Fassungen entstehen schon beim
Anlegen und liegen in der Ablage; der Bau kopiert sie nur.

**V8 (P1) Lizenz-Positivliste.** Angenommen: CC0, Public domain/PD, CC BY x.y, CC BY-SA x.y. Abgelehnt mit klarem Katalogtext: Free
Art License, CC BY-NC*, CC BY-ND*, GFDL-only, unbekannte oder fehlende Lizenz. Die Entscheidung trifft Frieda aus den Metadaten,
nicht Claude. Jede Ablehnung hat einen eigenen Katalogschlüssel unter `bild.abgelehnt.*` (`lizenz`, `nicht_gefunden`,
`kein_rasterbild` (auch SVG, Video, PDF), `zu_gross` (Bilddatei oder Metadaten über der Grenze), `netz` (Zeitüberschreitung, dauerhaft 429 oder 5xx), `grenze` (`max_anzahl` erreicht), `quelle` (keine oder beide Quellen),
`ziel` (`zu` unbekannt), `rolle` (Titelbild ohne Organisator-Rolle)), in Tests am Schlüssel geprüft. Fehlt bei einer Wikidata-Kennung P18, gilt `nicht_gefunden`.

**V9 (P1) Urheber säubern.** Das Urheberfeld von Commons ist HTML; es wird zu Text gesäubert und nie roh ausgeliefert.

### Hotlink-Sperre und Altbestand (P1, #581)

**V10 (P1) Nur eigene Bilder im Text.** Bilder im Text sind nur aus `medien/…` oder als `BI-…` erlaubt. `http(s)://…` und
`//host…` als Bildquelle sind ein Baufehler mit Katalogtext; der Schreibweg lehnt einen solchen Text über seinen Probebau mit
demselben Katalogtext ab, bevor er in die Reise kommt. Ein Link (`[Titel](https://…)`) bleibt erlaubt. Die Meta-CSP der Reiseseite erhält `img-src 'self' data:`; `blob:` nur,
wenn der Seitentest der Karte ohne `blob:` einen CSP-Fehler zeigt (Grund dann im PR). Dieser Seitentest (Karte mit Kacheln und
Ebenen-Symbol, Belege, App-Symbol unter der neuen CSP, ohne CSP-Fehler in der Konsole, Chromium und WebKit) gehört zu P1. Fälle in `test_sicherheit.py`, die heute fremde Bilder durchlassen, werden umgedreht.

**V11 (P1) `bilder_nachziehen` (Schritt in `neu.py nachziehen`, idempotent, mit Test).** Altbestand `![…](medien/x.jpg)` im Text
wird ein Eintrag in `bilder.yaml` mit `quelle: reise` (`zu` ist die ID des Abschnitts, in dem das Bild steht; ohne
erkennbaren Abschnitt `reise`) (Herkunft „aus der Reise übernommen“, ohne Lizenzfeld, die Nennung entfällt),
und der Text wird zu `![…](BI-NN)`. Ein fremdes Bild im Text wird ein normaler Link. Der Schritt liegt im selben PR wie die Sperre,
damit kein Bau einer vorhandenen Reise bricht.

**V10a (P1) `BI-` im Text schon in P1.** Der Bau löst `![…](BI-NN)` im Text auf die große Fassung des aktiven Bildes auf und zeigt
es wie bisher ein Bild aus `medien/` (gleiche Darstellung). Die große Fassung kommt dabei über den bestehenden Weg in die Offline-Liste (dieselbe Bilderliste des
Baus, aus der `pwa_schreiben` heute die Bilder aus `medien/` in `__DATEIEN__` des Service Workers schreibt); P2 löst das durch V20 ab. Darunter steht
schon in P1 die Namensnennung nach V16 als kleine Zeile (Urheber · Lizenz als Link · Commons-Seite), damit kein fremdes Bild ohne
Nennung erscheint; P2 ersetzt die Zeile durch den Baustein aus V15. Ein zurückgezogenes Bild entfällt aus dem Text ohne Fehler;
eine unbekannte Kennung ist ein Baufehler mit Katalogtext. Damit sehen Reisen mit Altbestand nach `bilder_nachziehen` aus wie vorher.
Für `quelle: reise` erzeugt `bilder_nachziehen` die beiden WebP-Fassungen aus der vorhandenen Datei (ohne Netz); die Originaldatei
bleibt in der Ablage.

### Bau und Darstellung (P2)

**V12 (P2) Bau.** Der Bau übergibt aktive Bilder an die Vorlage und kopiert die Fassungen. `![](BI-03)` im Text wird als Bild
gezeigt, ebenso ein Bildlink im Satz auf ein Bild der Reise. Die bestehende Pipeline für JPEG unter `medien/` bleibt unverändert.
Überschreitung der Offline-Grenze: Warnung (V3).

**V13 (P2) Titelbild.** Bild 16:10 mit großem Radius (Token `--radius-gross` der Vorlage, sonst 16 px) ganz oben auf der Startseite, darunter klein die Namensnennung, darunter der
Reisekopf wie heute. In der Tagesliste steht rechts ein Vorschaubild (44 px) bei Tagen mit Kopfbild; Tage ohne Bild bleiben
unverändert.

**V14 (P2) Kopfbild an der Heimat (ADR-0003).** Je Ding das erste Bild als Kopfbild 16:9: über dem Namen an der Ortsseite, über den
Kennzahlen bei der Etappe, über der großen Tageszahl am Tag, oben in der Karte der ersten Nacht bei der Unterkunft. Weitere Bilder
desselben Dings als Reihe (72×54) mit „n Bilder“. Alle anderen Stellen (z. B. die Unterkunft an Tag 3) zeigen nur eine Zeile mit
Mini-Vorschaubild und verweisen auf die Heimat.

**V15 (P2) Bild im Wissenstext.** In Spaltenbreite, mit Bildunterschrift (von Claude) und der von Frieda gesetzten Namensnennung.

**V16 (P1, P2) Namensnennung.** Urheber · Lizenz (als Link) · Commons-Seite; bei gemeinfreien Bildern nur der Urheber; bei
`quelle: reise` keine Nennung.

**V17 (P2) Großansicht.** Dunkler Hintergrund, Beschriftung „Ding · 1 / 3“, Schließen, Pfeile (am Handy ausgeblendet), Wischen
zwischen Bildern, Wischen nach unten schließt, Bildunterschrift und volle Nennung. Gruppe = Bilder desselben Dings. Bedienbar mit
Tastatur (Pfeile, Escape), Fokus wird gefangen und danach zurückgegeben.

**V18 (P2) Reise ohne Bilder.** Das Stadtwochenende erscheint exakt wie heute, keine Platzhalter, keine zusätzlichen Elemente.

**V19 (P2) Bausteine.** Jeder neue Baustein steht im Kopfkommentar der Vorlage, in den Stilen seiner Ebene, auf der Bausteinseite
und in `docs/design.md`; ist er eine Grundform-Darstellung, auch in `GRUNDFORMEN`. Alle sichtbaren Texte (Nennung, „n Bilder“,
„Schließen“, Großansicht, Ablehnungen, Werkzeugbeschreibung) stehen in allen `texte_<kürzel>.py`; die Ausnahmelisten in
`test_texte.py` werden nicht länger.

**V20 (P2) Service Worker.** Vorab werden die kleine Fassung aller Bilder und die große von Titel- und Kopfbildern geladen; übrige
große Fassungen beim Ansehen. Die Offline-Pipeline für JPEG unter `medien/` bleibt unverändert.

### Meine Reisen und Doku (P3)

**V21 (P3) Kachel.** „Meine Reisen“ zeigt Kacheln: Titelbild 16:7 (kleine Fassung) über eine angemeldete Konnektor-Route
`/bild/<reise>/<BI>.webp` (`<reise>` ist der Ordnername der Reise, wie ihn `my_trips` nennt, nicht der geheime Link) mit Prüfung der Mitgliedschaft und `Cache-Control: private`. Der geheime Reiselink taucht in der Seite und
in der Adresse nie auf. Ohne Titelbild: ruhige Fläche in Akzentfarbe mit dem App-Symbol der Reise, nie ein leerer Kasten. Das Archiv
bleibt in `<details>`. Kein Mitglied: kein Bild (gleiche Antwort wie „nicht vorhanden“).

**V22 (P3) Doku.** `docs/konnektor.md` (Werkzeuge, Aliase, Rechte, Lizenzregel; die Werkzeugliste selbst schon in P1, damit
`test_design.py` grün bleibt), `docs/design.md` (Bausteine), `docs/ontologie.md`
(Bild als Eigenschaft der Grundformen), Verlauf in `docs/adr/0001-kern.md`.

### Beispielreise und Betrieb (P1, P2)

**V23 (P1) Modul.** `engine/bilder.py` steht in `KN_MODULE` und `SB_MODULE` in `betrieb/deploy.sh`.

**V24 (P1, P2) Beispielreise.** Die Beispielreise erhält wenige kleine echte freie Bilder (mit Titelbild), Lizenz und Urheber in
`THIRD_PARTY.md`, als Beispielwert markiert. P1 legt Daten und Dateien an und zeigt ein Bild im Wissenstext (V10a) mit Nennung; Titelbild und Kopfbilder zeigt erst P2. Das Stadtwochenende bleibt ohne Bilder.

## Grenzen und Nicht-Ziele

- Keine eigenen Fotos, kein Hochladen, kein echtes Löschen (Stufe 2, #582).
- Keine Bildersuche durch Frieda; Claude nennt die Datei oder Kennung.
- Keine anderen Quellen als Commons und Wikidata.
- Kein Bild als Grundform, Art oder Merkmal; keine reisespezifische Logik in der Engine.
- Keine KI in Frieda; Claude wählt aus, die Lizenzprüfung ist deterministisch.
- Kein Netz in Tests.

## Test Plan

### P1

- `test_bilder.py` (neu, Commons- und Wikidata-Antworten als Fixtures, Abruffunktionen per `monkeypatch`, kleines Testbild):
  - GIVEN eine Commons-Antwort mit CC BY-SA 4.0 WHEN `image_add` THEN Eintrag mit Urheber (gesäubert), Lizenz, Links, beiden
    WebP-Fassungen (480 und 1600 px) in der Ablage.
  - GIVEN je Fixture CC0, PD, CC BY 3.0 THEN angenommen; GIVEN Free Art License, CC BY-NC, CC BY-ND, GFDL-only, fehlende Lizenz
    THEN abgelehnt mit Katalogtext.
  - GIVEN ein Urheberfeld mit HTML und Skript THEN der Eintrag enthält nur Text.
  - GIVEN eine Wikidata-Kennung mit P18 THEN wird die Datei aufgelöst; GIVEN ohne P18 THEN Ablehnung.
  - GIVEN SVG, PDF oder beschädigte Bytes WHEN `image_add` THEN abgelehnt.
  - GIVEN 429 dann 200 THEN eine Wiederholung gelingt; GIVEN dauerhaft 5xx oder Zeitüberschreitung THEN Katalogtext ohne Eintrag.
  - GIVEN eine Datei über 15 MB THEN Ablehnung vor der Verkleinerung.
  - GIVEN `image_add` mit `title_image` durch `mitwirkend` THEN Ablehnung; durch `organisator` THEN Titelbild gesetzt.
  - GIVEN 60 aktive Bilder WHEN `image_add` THEN Ablehnung; GIVEN `max_anzahl` in `reise.yaml` höher THEN angenommen.
  - GIVEN `![](BI-NN)` im Text THEN steht die große Fassung in `__DATEIEN__` des gebauten Service Workers (`test_pwa.py`).
  - GIVEN `zu: reise` THEN angenommen; GIVEN `mitwirkend` THEN darf zurückziehen und wiederherstellen.
  - GIVEN ein Commons-Bild per `![](BI-NN)` im Text THEN steht die Nennung (Urheber, Lizenz-Link, Commons-Seite) darunter; bei
    gemeinfrei nur Urheber; bei `quelle: reise` keine Nennung.
  - GIVEN Metadaten-Antwort über 1 MB THEN `bild.abgelehnt.zu_gross`.
  - GIVEN `zu` auf unbekannte ID THEN Ablehnung; GIVEN zwei Quellen oder keine THEN Ablehnung.
  - GIVEN Rolle `gast` THEN abgelehnt; `mitwirkend` darf hinzufügen und ändern, aber kein Titelbild; `organisator` setzt es und löst
    das bisherige ab (höchstens ein Titelbild).
  - GIVEN `zurueckziehen` THEN `status` zurückgezogen, Dateien bleiben, `wiederherstellen` kehrt es um.
  - GIVEN `BI-03` und `B-03` THEN werden beide erkannt und nicht verwechselt (`neu`, `routen`, `schreiben`).
  - GIVEN Abruf THEN läuft er vor der Schreibsperre (Vorab-Muster) und der Aufruf nutzt `instanz.kennung()` als User-Agent.
  - GIVEN `![](BI-03)` im Text THEN der Bau zeigt das Bild (große Fassung, im Precache); zurückgezogen THEN entfällt ohne
    Fehler; unbekannte Kennung THEN Baufehler.
  - `bilder_nachziehen`: GIVEN `![](medien/x.jpg)` THEN Eintrag `quelle: reise` mit beiden WebP-Fassungen und Text `![](BI-NN)`, der
    Bau zeigt das Bild weiter; GIVEN fremdes Bild THEN Link;
    zweiter Lauf ändert nichts; Stadtwochenende unverändert.
  - Werkzeug-Schemas und Aliase: englische Namen mit deutschem Alias (`bild_hinzufuegen`, `bild_aendern`), `MitBild` in der Antwort.
- `test_sicherheit.py`: GIVEN `![](https://…)` und `![](//host/…)` THEN Baufehler mit Katalogtext (bisher durchgelassen, Fälle
  umgedreht), und der Schreibweg (z. B. `knowledge_write`) lehnt denselben Text ab; GIVEN `[Titel](https://…)` THEN erlaubt; GIVEN `![](medien/…)` und `![](BI-…)` THEN erlaubt; Meta-CSP enthält `img-src 'self' data:`.
- `test_design.py` (Werkzeugliste in `docs/konnektor.md` gleich dem Bestand), `test_betrieb.py` (Modulliste enthält `bilder.py`),
  `test_texte.py` (alle neuen Schlüssel in allen Sprachen, Ausnahmelisten nicht länger), Ablage-Tests: Export und Löschen der Reise
  nehmen die Bilddateien mit.
- Seitentest (Chromium und WebKit, Beispielreise): Karte mit Kacheln und Ebenen-Symbol, Belege und App-Symbol unter der neuen CSP
  ohne CSP-Fehler in der Konsole; ein `![](BI-NN)` im Text wird angezeigt.
- Tests der einbindenden Instanz mit dem Branch vor dem Vorspulen.

### P2

- `test_bilder.py`: GIVEN Beispielreise THEN `dist` enthält beide Fassungen, Vorlage-Daten tragen Nennung, zurückgezogene Bilder
  fehlen; GIVEN über 25 MB Offline THEN Warnung, Bau gelingt; Stadtwochenende enthält keine Bild-Elemente und keine Bilddaten.
- `test_pwa.py`: Precache enthält kleine Fassungen aller und große von Titel-/Kopfbildern; JPEG-Pipeline unverändert; Altbestand-Tests
  (`test_bauen.py`, `test_pwa.py`) bleiben grün.
- Playwright-Seitentests (neu, Chromium und WebKit): Titelbild mit Nennung, Vorschaubild in der Tagesliste, Kopfbild an Ort, Etappe,
  Tag und Unterkunft (erste Nacht), Bildreihe mit „n Bilder“, Mini-Vorschau an anderer Stelle, Bild im Wissenstext mit Unterschrift
  und Nennung; Großansicht (Öffnen, „Ding · 1 / 3“, Pfeile, Escape, Wischen, Wischen nach unten, Pfeile am Handy ausgeblendet);
  Karte lädt mit den neuen Bausteinen weiter ohne CSP-Fehler; Handybreite (360 px) ohne Überbreite; Stadtwochenende
  ohne Bild-Elemente und unverändert.

### P3

- `test_bilder.py` und `test_anmeldung.py`: GIVEN Mitglied WHEN `/bild/<reise>/<BI>.webp` THEN 200 mit kleiner Fassung und
  `Cache-Control: private`; GIVEN Nicht-Mitglied oder nicht angemeldet THEN keine Auslieferung; zurückgezogenes Bild wird nicht
  ausgeliefert; weder die Bildadresse noch die Konto-Seite enthalten den geheimen Reiselink; Kachel ohne Titelbild zeigt Akzentfläche mit Symbol.
- Seitentest „Meine Reisen“ (Chromium und WebKit): Kachel mit und ohne Titelbild, Archiv in `<details>`, Handybreite.

## Acceptance Criteria

- **AC-1 (P1):** Given eine Commons-Datei oder eine Wikidata-Kennung mit freier Lizenz / When `image_add` mit `zu` aufgerufen wird / Then entsteht `BI-NN` mit Herkunft, gesäubertem Urheber, Lizenz und beiden WebP-Fassungen, und die Antwort an Claude zeigt eine kleine Vorschau.
- **AC-2 (P1):** Given eine Lizenz außerhalb der Positivliste (Free Art, NC, ND, GFDL-only, unbekannt) / When `image_add` / Then Ablehnung mit dem passenden Schlüssel `bild.abgelehnt.*` und kein Eintrag.
- **AC-3 (P1):** Given Rolle `mitwirkend` / When Bild hinzufügen, ändern, zurückziehen oder Titelbild setzen / Then alles außer dem Titelbild gelingt; Given `organisator` / When Titelbild setzen / Then es gibt genau ein Titelbild.
- **AC-4 (P1):** Given ein zurückgezogenes Bild / When gebaut wird / Then fehlt es überall, bleibt aber in Liste und Ablage; Given 60 aktive Bilder / When ein weiteres / Then Ablehnung, außer `max_anzahl` in `reise.yaml` ist höher.
- **AC-5 (P1):** Given Commons antwortet mit 429 und dann 200 / When `image_add` / Then gelingt der Abruf vor der Schreibsperre mit Zeitlimit 20 s und User-Agent aus `instanz.kennung()`; kein Test benutzt das Netz.
- **AC-6 (P1):** Given ein Text mit `![](https://…)` oder `![](//host/…)` / When gebaut oder über den Schreibweg geschrieben wird / Then Fehler mit Katalogtext; Links bleiben erlaubt; die Meta-CSP enthält `img-src 'self' data:` (`blob:` nur nach V10 mit Grund im PR-Text), und der Seitentest zeigt Karte, Belege und App-Symbol ohne CSP-Fehler in Chromium und WebKit.
- **AC-7 (P1):** Given eine Reise mit `![](medien/x.jpg)` und einem fremden Bild im Text / When `neu.py nachziehen` zweimal läuft / Then Altbestand steht als `BI-NN` mit `quelle: reise` in `bilder.yaml`, das fremde Bild ist ein Link, der zweite Lauf ändert nichts, und der Bau gelingt.
- **AC-8 (P1):** Given `![…](BI-NN)` im Text / When gebaut wird / Then erscheint das Bild mit Namensnennung nach V16 und seine große Fassung steht in der Offline-Liste des Service Workers.
- **AC-9 (P1):** Given `BI-03` und `B-03` / When `neu`, `routen` und `schreiben` Kennungen erkennen / Then werden sie nie verwechselt; `bilder.py` steht in `KN_MODULE` und `SB_MODULE`.
- **AC-10 (P1):** Given der Branch / When die volle Testsuite und die Tests der einbindenden Instanz laufen / Then sind beide grün (Nachweis im PR-Text).
- **AC-11 (P2):** Given die Beispielreise / When die Seite in Chromium und WebKit (auch 360 px) geöffnet wird / Then zeigen Titelbild, Vorschau in der Tagesliste, Kopfbild an der Heimat, Bildreihe, Mini-Vorschau, Bild im Text und Großansicht die Maße und Stellen aus V13 bis V17 mit Nennung nach V16, ohne Überbreite.
- **AC-12 (P2):** Given das Stadtwochenende / When gebaut und geöffnet wird / Then enthält es keine Bild-Elemente und keine Bilddaten.
- **AC-13 (P2):** Given die neuen Bausteine / When die Karte geöffnet wird / Then lädt sie ohne CSP-Fehler (Seitentest aus P1 bleibt grün).
- **AC-14 (P2):** Given aktive Bilder / When gebaut wird / Then enthält die Offline-Liste die kleine Fassung aller und die große von Titel- und Kopfbildern; Given über `offline_mb` / Then Warnung, der Bau gelingt.
- **AC-15 (P2):** Given neue Bausteine und Texte / When die Prüfungen von Bausteinseite und Texten laufen / Then stehen sie in Kopfkommentar, Bausteinseite, `docs/design.md` und allen Sprachdateien.
- **AC-16 (P3):** Given ein Mitglied mit Titelbild / When „Meine Reisen“ geöffnet wird / Then zeigt die Kachel das Bild über `/bild/<reise>/<BI>.webp` (Ordnername, `Cache-Control: private`), ohne Titelbild die Akzentfläche mit App-Symbol; Given Nicht-Mitglied / Then kein Bild; der geheime Link taucht nie auf.
- **AC-17 (P3):** Given P3 ist ausgeliefert / When die Doku geprüft wird / Then sind `docs/konnektor.md`, `docs/design.md`, `docs/ontologie.md` und der ADR-0001-Verlauf nachgeführt.

## Definition of Done

- [ ] Alle Acceptance Criteria des Pakets sind erfüllt und durch Tests belegt.
- [ ] Die volle Testsuite ist ohne echte Reisen grün; die Seitentests laufen in Chromium und WebKit.
- [ ] Die Tests der einbindenden Instanz laufen mit dem Branch grün.
- [ ] Jedes Paket ist mit grünen Pflichtprüfungen ausgeliefert und auf dem Server der Instanz aktiv.
- [ ] Vorhandene Reisen sind mit `neu.py nachziehen` umgestellt und veröffentlichen ohne Fehler.
- [ ] Doku (V22) und Bausteinseite sind nachgeführt; #455 (Stufe 1) und #581 werden erst nach P3 geschlossen.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine neue; Verlauf in ADR-0001.
- **Rationale:** Das Bild folgt dem Muster der Packliste (eigene Liste, Eigenschaft der Grundformen) und bleibt im Rahmen von
  ADR-0001 (keine neue Grundform) und ADR-0003 (eine Heimat je Grundform); der Verlauf in ADR-0001 hält fest, dass Bilder zu den
  Eigenschaften der Grundformen gehören.

## Changelog

- 2026-11-15: Erste Fassung der Spec (Stufe 1 aus #455 mit #581), drei Pakete.
