---
entity_id: bilder-lizenzhinweis-613
type: feature
created: 2026-11-17
updated: 2026-11-17
status: draft
workflow: 613-lizenzpruefung-entfernen
version: "1.0"
tags: [bilder, lizenz, nutzungsrechte, konnektor, schreibweg]
---

# Bilder: Lizenzprüfung entfällt, Hinweis zu Nutzungsrechten (#613)

## Approval

- [ ] Approved

## Purpose

Frieda prüft Urheberschaft und Lizenz eines Commons-Bildes nicht mehr selbst (Vorgabe des Product Owners, 17.11.2026, Teil von
#455). Jedes Commons-Bild wird angenommen; die Verantwortung für die Nutzungsrechte liegt bei der Person, die das Bild
hinzufügt. Statt einer Sperre bekommt sie in der Antwort von `image_add` einen Hinweis: Urheber und Lizenz, die Erinnerung an die
eigene Verantwortung und, bei eingeschränkten Lizenzen, was genau eingeschränkt ist. Der Hinweis informiert nur, er sperrt nie.

## Source

- **Ersetzt:** Lizenzregel V8 der Spec `docs/specs/oberflaeche/bilder-455-stufe1.md` (Positivliste CC0, gemeinfrei, CC BY,
  CC BY-SA; Ablehnung `bild.abgelehnt.lizenz`). Die alte Spec bleibt als Geschichte unverändert; ab dieser Spec gilt V8 nicht mehr.
- **Kontext und Analyse:** `docs/context/613-lizenzpruefung-entfernen.md` (Abschnitt „Analysis“ verbindlich).
- **Files:** `engine/bilder.py`, `engine/schreiben.py`, `engine/texte_de.py`, `engine/texte_en.py`, `docs/konnektor.md`,
  `engine/tests/test_bilder.py`.
- **Identifier:** `bilder.lizenz_lesen`, `bilder.einschraenkungen`, `schreiben.bild_hinzufuegen`.

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `engine/bilder.py` (`abrufen`, `gemeinfrei`, `GEMEINFREI`, `urheber_saeubern`) | module | Abruf der Commons-Angaben; Gemeinfrei-Erkennung bleibt |
| `engine/bauen.py` (`nennung_daten`, `nennung_html`) | module | Namensnennung unter dem Bild, unverändert |
| `engine/texte_<kürzel>.py`, `docs/sprachen.md`, `engine/tests/test_texte.py` | Regel | Texte in allen Sprachen, Ausnahmelisten nur kürzer |
| `docs/specs/oberflaeche/bilder-455-stufe1.md` | Spec | V8 wird ersetzt |
| Wikimedia Commons `extmetadata` | extern | `LicenseShortName`, `LicenseUrl`, `Artist`; in Tests kein Netz |
| Tests der einbindenden Instanz | Betrieb | Meldungstexte ändern sich, vor dem Vorspulen mit dem Branch laufen lassen |

## Scope

**Gehört dazu:** Positivliste und Ablehnung entfernen; Einordnung der Lizenz als reine Funktion; Antwort von `image_add` mit
Urheber, Lizenz, Verantwortungshinweis und Einschränkungen; Werkzeugbeschreibung und Konnektor-Doku; Tests.

**Nicht Teil:** eigene Fotos (#582, übernimmt später die Verantwortungsangabe); Änderung der Namensnennung auf der Seite;
neues Feld in `plan/bilder.yaml`; Ablehnungen für Netz, Format, Größe, Quelle, Ziel, Grenze und Rolle (bleiben).

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `engine/bilder.py` | MODIFY | `FREI` und `lizenz_pruefen` entfallen; `lizenz_lesen` (wirft nie) und `einschraenkungen(lizenz)` neu; `abrufen` und Kopf-Docstring angepasst |
| `engine/schreiben.py` | MODIFY | `bild_hinzufuegen`: Antwort aus `bild.neu` mit Ersatzwörtern, `bild.rechte` und je Einschränkung ein Satz; Docstring „Lizenz lesen“ |
| `engine/texte_de.py` | MODIFY | `bild.abgelehnt.lizenz` entfernt; neue Schlüssel (siehe unten); Werkzeugbeschreibung ohne Positivliste |
| `engine/texte_en.py` | MODIFY | wie `texte_de.py`, englisch |
| `docs/konnektor.md` | MODIFY | Zeile zu `image_add`/`bild_hinzufuegen`: Positivliste raus, Hinweis statt Ablehnung |
| `engine/tests/test_bilder.py` | MODIFY | Positivlisten- und Ablehnungstests ersetzen, neue Tests (siehe Test Plan) |

### Estimated Changes

- Files: 6
- LoC: +90/-40

## Implementation Details

### bilder.lizenz_lesen

Liest aus `extmetadata` und gibt `{"lizenz", "lizenz_url", "gemeinfrei"}` zurück, wie bisher. Sie wirft nie wegen der Lizenz. Eine
fehlende oder leere Lizenz ergibt `lizenz == ""`, `lizenz_url == None`, `gemeinfrei == False`. Name und Lizenz-Link werden wie
bisher gesäubert (`urheber_saeubern`, nur `https://`-Links). `abrufen` ruft sie auf; das Ergebnis-Dict (und damit der Vorab-Weg als
JSON) behält seine Form. Es entsteht kein neues Feld und keine neue Ablehnung.

### bilder.einschraenkungen

Reine Funktion ohne Netz: `einschraenkungen(lizenz) -> list[str]`. Reihenfolge der Prüfung und Ergebnis:

1. leer oder nur Leerraum: `["fehlt"]`
2. gemeinfrei nach `GEMEINFREI` (CC0, Public domain, PD…): `[]`
3. Muster `CC BY` oder `CC BY-SA`, Version und Sprachkürzel optional (`CC BY-SA 3.0`, `CC BY-SA`, `CC BY 4.0 de`): `[]`
4. sonst enthält der Name (als eigenes Wort, ohne Beachtung der Schreibweise) `NC`: `nc`; enthält `ND`: `nd`; enthält `GFDL`: `gfdl`;
   mehrere möglich, Reihenfolge `nc`, `nd`, `gfdl`
5. nichts davon trifft zu (Free Art License, „Copyrighted“, „Attribution“, …): `["andere"]`

### Einordnungstabelle

| Lizenzname (Beispiel) | `einschraenkungen` | Hinweis in der Antwort |
|---|---|---|
| `CC0` | `[]` | nur Urheber, Lizenz, Verantwortung |
| `Public domain` | `[]` | wie oben |
| `CC BY 4.0` | `[]` | wie oben |
| `CC BY-SA 3.0` | `[]` | wie oben |
| `CC BY-SA` (ohne Version) | `[]` | wie oben |
| `CC BY-NC 4.0` | `["nc"]` | nicht für kommerzielle Nutzung |
| `CC BY-NC-ND 4.0` | `["nc", "nd"]` | beide Sätze: nicht kommerziell, keine Bearbeitung |
| `CC BY-ND 2.0` | `["nd"]` | keine Bearbeitung (auch Beschnitt und Verkleinerung) |
| `GFDL` | `["gfdl"]` | Lizenz für Dokumentation; Weitergabe nur mit Lizenztext |
| `Free Art License` | `["andere"]` | Lizenz nicht eingeordnet, Bedingungen selbst prüfen |
| `Copyrighted` | `["andere"]` | wie oben |
| `` (leer) | `["fehlt"]` | keine Lizenzangabe gefunden |

Wichtig für die Bearbeitung: Frieda zeigt das Bild verkleinert und beschnitten (`object-fit: cover`); bei `nd` sagt der Satz das offen.

### Aufbau der Antwort von bild_hinzufuegen

Die Antwort setzt sich aus Katalogsätzen zusammen, getrennt durch ein Leerzeichen, in dieser Reihenfolge:

1. `schreiben.antwort.bild.neu` (besteht, mit `{bid}`, `{zu}`, `{urheber}`, `{lizenz}`)
2. `schreiben.antwort.bild.rechte` (immer)
3. je Code aus `einschraenkungen` ein Satz `schreiben.antwort.bild.einschraenkung.<code>` mit `<code>` aus `nc`, `nd`, `gfdl`, `fehlt`, `andere`

Ersatzwörter, damit keine leeren Stellen („: , .“) entstehen: Ist der Urheber leer, steht `schreiben.antwort.bild.ohne_urheber`
(„Urheber nicht angegeben“); ist die Lizenz leer, steht `schreiben.antwort.bild.ohne_lizenz` („Lizenz nicht angegeben“). Das
Ersetzen betrifft nur die Antwort; gespeichert wird der leere Wert wie bisher (die Namensnennung der Seite behandelt ihn schon).

Deutsche Beispieltexte (Wortlaut im Katalog darf geringfügig abweichen, Inhalt nicht):

- `schreiben.antwort.bild.neu`: „Bild {bid} zu {zu} hinzugefügt: {urheber}, {lizenz}. Die Vorschau zeigt, was Frieda abgelegt hat.“
- `schreiben.antwort.bild.rechte`: „Frieda prüft die Nutzungsrechte nicht. Du bist dafür verantwortlich, dass du das Bild so verwenden darfst; Urheber und Lizenz stehen unter dem Bild.“
- `…einschraenkung.nc`: „Die Lizenz schließt kommerzielle Nutzung aus (NC). Für eine öffentliche oder kommerzielle Reise ist das Bild dann nicht geeignet.“
- `…einschraenkung.nd`: „Die Lizenz erlaubt keine Bearbeitung (ND). Frieda verkleinert und beschneidet das Bild für die Anzeige; das kann bereits eine Bearbeitung sein.“
- `…einschraenkung.gfdl`: „Das Bild steht unter der GFDL, einer Lizenz für Dokumentation. Die Weitergabe verlangt meist den Lizenztext; die Bedingungen bitte selbst prüfen.“
- `…einschraenkung.fehlt`: „Für das Bild fand Frieda keine Lizenzangabe. Ohne Lizenz sind die Nutzungsrechte ungeklärt; bitte auf der Commons-Seite nachsehen.“
- `…einschraenkung.andere`: „Frieda kennt diese Lizenz nicht und kann nicht sagen, was sie erlaubt. Bitte die Bedingungen auf der Commons-Seite lesen.“
- `ohne_urheber`: „Urheber nicht angegeben“; `ohne_lizenz`: „Lizenz nicht angegeben“.

Die Einschränkung wird in `schreiben` aus dem gespeicherten Lizenznamen abgeleitet (`einschraenkungen(b["lizenz"])`); der
Vorab-Weg (Abruf vor der Sperre als JSON) bleibt unverändert.

### Werkzeugbeschreibung und Konnektor-Doku

`konnektor.werkzeug.bild_hinzufuegen` (de und en) nennt keine Positivliste mehr. Sie sagt: Jedes Bild von Wikimedia Commons wird
angenommen und mit Namensnennung gezeigt; Frieda prüft die Nutzungsrechte nicht, die Person ist dafür verantwortlich; die Antwort
nennt Urheber, Lizenz und mögliche Einschränkungen, und Claude gibt diesen Hinweis an die Person weiter. `docs/konnektor.md`
übernimmt dieselbe Aussage.

### Prüfstelle ADR-0001

Keine Änderung des Kerns: Bild bleibt Eigenschaft der Grundformen; keine Art, kein Merkmal, keine KI in Frieda (der Hinweis ist
eine feste Regel im Code mit Katalogtexten); beide Beispielreisen werden durchgespielt (siehe AC-2); kein Formatwechsel der
Reisedaten.

## Test Plan

### Automated Tests (TDD RED)

Alle in `engine/tests/test_bilder.py` (Fixtures `wanderung`, `stadt`, `Netz`, `meta`, `commons_antwort`, `neu_hinzu` nutzen); die
Positivlisten-Tests (`test_lizenz_positivliste_nimmt_an`, `test_lizenz_ausserhalb_der_positivliste_wird_abgelehnt`,
`test_bild_mit_unfreier_lizenz_kommt_nicht_in_die_reise`) und der Kopf-Docstring werden ersetzt.

- [ ] GIVEN `extmetadata` mit einer beliebigen Lizenz, auch leer WHEN `lizenz_lesen` THEN wirft sie nie, liefert `lizenz`,
  `lizenz_url`, `gemeinfrei` (CC0 und Public domain gemeinfrei, sonst nicht; leere Lizenz `""`).
- [ ] GIVEN die Tabelle oben WHEN `einschraenkungen(name)` (parametrisiert) THEN genau die Codes der Tabelle in der Reihenfolge `nc`, `nd`, `gfdl`.
- [ ] GIVEN die Wanderung und je eine Lizenz aus CC BY-NC 4.0, CC BY-ND 4.0, CC BY-NC-ND 4.0, GFDL, Free Art License, Copyrighted, leer
  WHEN `bild_hinzufuegen` THEN kein Fehler, Eintrag in `plan/bilder.yaml` mit dieser Lizenz und beide Fassungen vorhanden.
- [ ] GIVEN dieselben Fälle am Stadtwochenende (Fixture `stadt`) WHEN `bild_hinzufuegen` THEN ebenfalls angenommen.
- [ ] GIVEN eine eingeschränkte Lizenz WHEN die Antwort gebildet wird THEN enthält sie Urheber, Lizenz, den Rechtehinweis und den
  Satz der Einschränkung (Prüfung gegen die Katalogtexte, nicht gegen feste Wörter); bei CC BY-NC-ND beide Sätze; bei CC BY 4.0 nur Rechtehinweis.
- [ ] GIVEN leerer Urheber oder leere Lizenz WHEN die Antwort gebildet wird THEN stehen die Ersatzwörter, kein „: ,“, kein doppeltes
  Leerzeichen, keine leere Stelle vor einem Punkt.
- [ ] GIVEN die Wanderung und das Stadtwochenende mit je einem angenommenen Bild unter eingeschränkter und unter fehlender Lizenz
  WHEN der Eintrag in `plan/bilder.yaml` gelesen und danach `neu.nachziehen(reise_dir, schreiben=False)` aufgerufen wird THEN
  enthält der Eintrag genau die Felder wie bei einem freien Bild (`datei`, `urheber`, `lizenz`, `lizenz_url`, `seite` und die
  bestehenden Pflichtfelder, kein neues), und `nachziehen` meldet für die Bilder nichts und ändert keine Datei (AC-8).
- [ ] GIVEN ein angenommenes Bild mit NC-Lizenz WHEN die Reise gebaut wird THEN zeigt die Seite die Namensnennung mit Urheber und Lizenz (Lizenz-Link) und der Bau gelingt.
- [ ] GIVEN ein Abruf mit Netzfehler, falschem Format, zu großer Datei oder zwei Quellen WHEN `bild_hinzufuegen` THEN bleibt die Ablehnung
  mit ihrem Schlüssel (bestehende Tests grün).
- [ ] GIVEN die Kataloge aller Sprachen WHEN `test_texte.py` läuft THEN fehlt `bild.abgelehnt.lizenz` überall, die neuen Schlüssel
  stehen in de und en, die Ausnahmelisten sind nicht länger.
- [ ] GIVEN die Werkzeugbeschreibung und `docs/konnektor.md` THEN nennen sie keine Positivliste mehr (`test_werkzeugliste_der_doku_nennt_die_bildwerkzeuge` bleibt grün).

## Acceptance Criteria

- **AC-1:** Given ein Commons-Bild mit beliebiger oder fehlender Lizenz / When `image_add` es hinzufügt / Then wird es
  angenommen; `bild.abgelehnt.lizenz` wird nirgends mehr geworfen.
- **AC-2:** Given die Beispielreise (`beispiel/reisen/beispielreise`) und das Stadtwochenende
  (`beispiel/reisen/stadtwochenende`) / When ein Bild mit NC, ND, GFDL, Free Art License, „Copyrighted“ oder ohne Lizenz hinzugefügt
  wird / Then wird es an beiden Reisen angenommen.
- **AC-3:** Given ein angenommenes eingeschränktes Bild / When die Reise gebaut wird / Then zeigt die Seite die Namensnennung
  mit Urheber und Lizenz unter dem Bild (gemeinfreie Bilder nur den Urheber, wie bisher).
- **AC-4:** Given die Antwort von `image_add` / When die Lizenz frei ist (CC0, gemeinfrei, CC BY, CC BY-SA mit oder ohne
  Version) / Then nennt sie Urheber, Lizenz und die Verantwortung der Person, ohne Einschränkungssatz.
- **AC-5:** Given die Antwort von `image_add` / When die Lizenz NC, ND, GFDL, unbekannt oder fehlend ist / Then steht zusätzlich
  je Einschränkung ein Satz, der sagt, was eingeschränkt ist; bei mehreren Einschränkungen alle.
- **AC-6:** Given leerer Urheber oder leere Lizenz / When die Antwort gebildet wird / Then stehen Ersatzwörter aus dem Katalog und
  keine leeren Stellen.
- **AC-7:** Given die Kataloge / When sie geprüft werden / Then existiert `bild.abgelehnt.lizenz` in keiner Sprache, die neuen
  Schlüssel stehen in jeder Sprache, und die Ausnahmelisten in `test_texte.py` sind nicht länger.
- **AC-8:** Given `plan/bilder.yaml` / When Bilder hinzugefügt werden / Then gibt es kein neues Feld, und `neu.py nachziehen`
  ändert nichts (kein Formatwechsel).
- **AC-9:** Given Abrufe mit Netzfehler, nicht unterstütztem Format, Größe über 15 MB oder falscher Quellenangabe / When
  `image_add` aufgerufen wird / Then bleiben die Ablehnungen `bild.abgelehnt.netz`, `kein_rasterbild`, `zu_gross` und `quelle` wie bisher.
- **AC-10:** Given Werkzeugbeschreibung und `docs/konnektor.md` / When gelesen / Then nennen sie keine Positivliste, sondern
  Verantwortung der Person und den Hinweis in der Antwort.

## Definition of Done

- [ ] AC-1 bis AC-10 sind erfüllt und durch Tests belegt; die volle Testsuite ist ohne echte Reisen grün.
- [ ] Die Tests der einbindenden Instanz laufen mit dem Branch grün, bevor vorgespult wird (Meldungstexte ändern sich).
- [ ] Ausgeliefert mit grünen Pflichtprüfungen; vorhandene Reisen veröffentlichen ohne Fehler.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine
- **Rationale:** Produktvorgabe des Owners ersetzt eine Regel (V8) innerhalb des bestehenden Bilder-Moduls; der Kern (ADR-0001) und das
  Datenformat bleiben unberührt, es entsteht keine neue Grundform und kein neues Feld.

## Known Limitations

- Die Einordnung erkennt nur CC-Namen, GFDL, gemeinfrei und leer; jede andere Lizenz gilt als „andere“ und wird nur genannt, nicht bewertet.
- Frieda ersetzt keine Rechtsberatung; der Hinweis ist eine Information, keine Prüfung.
- Eigene Fotos (#582) folgen später und übernehmen die Verantwortungsangabe.

## Changelog

- 2026-11-17: Initial spec created (#613); ersetzt Lizenzregel V8 aus `bilder-455-stufe1.md`.
- 2026-11-17: Test für AC-8 (kein neues Feld, `nachziehen` ändert nichts) im Test Plan ergänzt.
