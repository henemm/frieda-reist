---
entity_id: zeitleiste-bewegung-665
type: feature
created: 2026-11-24
updated: 2026-11-24
status: draft
workflow: fix-665-zeitleiste
tags: [oberflaeche, konnektor, waechter, kalender, zeit, merkmale, bewegung, atomic-design]
---

# Zeitleiste einer Bewegung (#665)

## Approval

- [ ] Approved

## Purpose

Eine Bewegung (Flug, Bahn, Fähre …) zeigt ihren Ablauf künftig als chronologische Zeitleiste: Abfahrt und Ankunft (fetter Name, gefüllter Punkt) und davor oder dazwischen weitere Zeitpunkte wie Online-Check-in, Gepäckabgabe oder Boarding, alle in einer Schriftgröße. Ein Merkmal wie das Terminal steht direkt bei dem Zeitpunkt, zu dem es gehört (`bei:`). Dafür darf ein Ding Zeitpunkt-Merkmale ohne Rolle tragen, eine Reise kann einzelne davon als „erinnert“ markieren, und die Buchung zeigt nur noch Geschäftliches (Nummer, Status, Preis, Zahlung, Reisende, Tarif, Beleg). Heute stehen die Zeiten in Definitionsreihenfolge als kleine graue Merkmale, und „Online-Check-in ab“ steht prominent im Buchungsblock.

## Source

- **File:** `engine/vorlage.html`
- **Identifier:** `function streckeZeile` (Heimat der Bewegung), neues Molekül `function zeitLeiste` (neu) mit den gemeinsamen Atomen `leistenPunkt`, `leistenZeit`, `leistenMarke`, `leistenZusatz` (neu, `halteLeiste` nutzt sie ebenfalls); Regeln in `engine/routen.py` (`lage_merkmale_falten`, `DEF_FELDER`, Lesen der Art-Definitionen), `engine/waechter.py` (`buchungsfristen`), `engine/kalender.py`

## Design-Entwurf (zur Freigabe vorgelegt)

Der Entwurf liegt als Claude-Artefakt vor (privat, erfundene Beispieldaten): https://claude.ai/artifact/7rvFwhZYkEhJ3mqb5Suez8, Version 3 (nach den Änderungen des Product Owners vom 24.11.2026). Quelltext der Seite im Repo: `docs/context/fix-665-entwurf.html`; für die Gestaltung maßgeblich, mit einer Ausnahme: Die Zeile „ein anderer Tag steht klein unter der Uhrzeit“ unter „Regeln dahinter“ ist veraltet, es gilt der Abschnitt „Zur Freigabe“ (abweichender Tag direkt bei der Uhrzeit, fett). Der Inhalt (Gestaltung und Regeln) steht als Kommentar im Issue #665. In Worten:

- **Aufbau:** eine senkrechte Punktleiste wie die Zwischenstopps (`ol.halte`, #509): links Punkt auf einer dünnen Linie, daneben die Uhrzeit (Ziffern gleich breit), rechts die Bezeichnung. Punkt und Linie, Uhrzeit-Ziffern, Marke und Zusatzzeile sind gemeinsame Atome mit der Halteleiste (siehe Atomic Design).
- **Eine Schriftgröße** für alle Uhrzeiten und Daten (Uhrzeit, Datum in der Kopfzeile, abweichendes Datum am Punkt). Abfahrt (`<Ort von>`) und Ankunft (`<Ort nach>`) heben sich nur ab durch **fetten Namen** und **gefüllten blauen Punkt** (Punkt wie im Entwurf: etwas größer als die leeren, 16 px statt 12 px; die Uhrzeit bleibt gleich groß). Alle übrigen Punkte: leerer Punkt (Rand grau), Bezeichnung ist der Name des Merkmals, nicht fett.
- **Kopfzeile unter dem Titel:** bei vorhandener Zeitleiste ohne Art-Name, nur das Datum der Fahrt (zum Beispiel „Fr 12.3.2027“), fett, in der Größe der Uhrzeiten. Die Art zeigt das Symbol im Titel.
- **Abweichendes Datum:** Ein Zeitpunkt, dessen Datum vom Tag der Fahrt abweicht, zeigt es mit Wochentag direkt bei der Uhrzeit, in ihrer Spalte unter ihr (wie im Entwurf: „07:05“, darunter „Mi 10.3.“), fett, gleiche Größe, nicht klein, nicht grau.
- **Marke „erinnert“:** kleine Marke in Warnfarbe hinter der Bezeichnung, an jedem Punkt, der erinnert.
- **Punkt aus der Buchung:** Bezeichnung ist `ab_was` der Buchung (ohne `ab_was` das Wort „ab“ aus `seite.buchung.ab`), darunter als Zusatzzeile „aus der Buchung“.
- **Zusatzzeile bei einem Punkt (`bei:`):** normale Schriftgröße, gedämpfte Farbe (wie `.zusatz` im Entwurf), unter der Bezeichnung; im Entwurf „Gepäckabgabe bis“ mit „Terminal 1, Schalter 20–28“.
- **Darunter:** die übrigen Merkmale (zum Beispiel Flugnummer) als Merkmalliste; Buchungsblock ohne ab-Zeile, sonst unverändert.

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `routen.lage_merkmale_falten`, `LAGE_TYPEN`, `TYP_FELD` | function / const | heute Fehler `pruefung.routen.lage_rolle` für `zeitpunkt` ohne Rolle (routen.py ~349–363); hier neu zugelassen |
| `routen.DEF_FELDER` und das Lesen der Art-Definitionen (routen.py ~490, ~1470–1510) | const / function | erlaubte Felder einer Merkmal-Definition; `erinnern` und `bei` kommen dazu, Prüfung der Ziele von `bei` nach dem Einlesen aller Merkmale der Art |
| `routen.zeitpunkt`, `ZEIT_MUSTER`, `lage_wert_gueltig` | function | Form von `zeitpunkt`: `HH:MM` oder `JJJJ-MM-TTTHH:MM` mit Zeitzone |
| `routen.buchung_termine`, `JE_DING_FELDER` | function | Buchungs-`ab` je Ding (#473), Quelle der Punkte aus der Buchung |
| `schreiben.merkmal_definieren` | function | Schreibweg für `attribute_define` (schreiben.py ~740–889, gespeicherte Schlüssel ~672 und ~885) |
| `konnektor.py`, `schnittstelle.py` | module | Parameter `erinnern` (englisch `remind`) und `bei` (englisch `at`) an `attribute_define`, wie `nach_buchung` / `visible_after_booking`; `bei` heißt in der Tabelle `PARAMETER` für alle Werkzeuge `booked_with` (Buchungsfeld „Gebucht bei“), deshalb Ausnahme in `PARAMETER_JE_WERKZEUG` für `merkmal_definieren`; Anzeige in `attributes` und `show` |
| `waechter.buchungsfristen` | function | Vorbild und Ort der neuen Erinnerung (waechter.py ~225–264) |
| `kalender.py` | module | Termine der Buchungs-`ab` (kalender.py ~196–198), Vorbild der neuen Termine |
| `vorlage.html`: `streckeZeile`, `halteLeiste`, `buchungBlock`, `planungsTeil`, `merkmalListe`, `merkmalWert`, `wertNachTyp`, `zeitText` | functions | Seite, Vorbild und Berührungspunkte; `merkmalWert` (Atom) zeigt den Wert eines Merkmals bei seinem Punkt |
| `engine/tests/test_design.py`, `docs/design.md`, Bausteinseite `ansichtBausteine`, `GRUNDFORMEN` | test / doc / code | die vier Stellen eines Bausteins (ADR-0002) |
| `texte_de.py`, `texte_en.py` (die Pseudo-Sprache der Tests leitet `test_texte.py` aus dem deutschen Katalog ab) | text | alle neuen Texte (ADR-0006) |
| ADR-0001 (Kern), ADR-0002 (Atomic Design), ADR-0003 (Heimat), ADR-0006, ADR-0007 | adr | Prüfstelle, neue Bausteine, eine Heimat je Grundform, Textkatalog, typisierte Merkmale |

## Scope

Dieser Auftrag umfasst **Schritt 1 (a, b, c) und die Zuordnung `bei:` (d)**. Ausdrücklich außerhalb: die Vorlage für die Art `flug` in `engine/artvorlagen` (Folge-Issue).

**Bewusste Abgrenzung (Risiko #619 klein halten):** Die neue Kopfzeile (nur Datum, ohne Art-Name) gilt **nur bei vorhandener Zeitleiste**. Ohne Zeitleiste bleibt die heutige Kopfzeile „Art · Datum · ab … → an …“ unverändert, ebenso in allen Kompaktansichten ohne `voll`. Die Zeilen der Bewegung ohne Zeitleiste werden nicht angefasst.

### Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| engine/routen.py | MODIFY | `zeitpunkt` ohne Rolle am Ding gültig (bleibt Merkmal, kein Falten); `erinnern` und `bei` in `DEF_FELDER` und in den übernommenen Feldern beim Lesen; Prüfung `erinnern` nur Typ `zeitpunkt`; Prüfung `bei` (Form, nicht an Typ `zeitpunkt`/`uhrzeit`, Ziel vorhanden); Hilfe, die die Zeitpunkte eines Dings für Seite, Wächter und Kalender liefert |
| engine/schreiben.py | MODIFY | `merkmal_definieren`: Eigenschaften `erinnern` (nur Typ `zeitpunkt`) und `bei` (anlegen, ändern, entfernen mit leerem Text, Ziel prüfen, Ändern des Typs eines Ziels ablehnen), gespeicherte Schlüssel um beide erweitert |
| engine/konnektor.py | MODIFY | Parameter `erinnern` und `bei` im Werkzeug-Schema von `attribute_define`, Anzeige „erinnert“ und „steht bei …“ in `attributes` und `show` |
| engine/schnittstelle.py | MODIFY | Alias `remind` für `erinnern`; Alias `at` für `bei` nur bei `merkmal_definieren` (`PARAMETER_JE_WERKZEUG`, weil `bei` sonst `booked_with` hieße) |
| engine/waechter.py | MODIFY | neue Erinnerung aus erinnerndem Zeitpunkt neben `buchungsfristen` |
| engine/kalender.py | MODIFY | ein Termin je erinnerndem Zeitpunkt mit eigener UID |
| engine/bauen.py | MODIFY | Seitendaten tragen die Zeitpunkte der Bewegung samt `erinnern` und die Zuordnung `bei` der Art-Merkmale (falls die Seite sie nicht schon aus `merkmale` der Art lesen kann) |
| engine/vorlage.html | MODIFY | gemeinsame Atome `leistenPunkt`, `leistenZeit`, `leistenMarke`, `leistenZusatz` und gemeinsame Stile (Punkt, Linie, Ziffern, Marke); neues Molekül `zeitLeiste`; `halteLeiste` nutzt die Atome (Aussehen unverändert); Einbau in `streckeZeile`; Kopfzeile bei Zeitleiste nur Datum; `buchungBlock` ohne ab-Zeile an der Bewegung; Zeitpunkte und `bei`-Merkmale aus der Merkmalliste genommen; Kopfkommentar „Bausteine nach Ebenen“, Stile der Ebenen, Bausteinseite `ansichtBausteine`, `GRUNDFORMEN` |
| engine/texte_de.py, engine/texte_en.py | MODIFY | neue Texte (siehe Implementation Details), `pruefung.routen.lage_rolle` angepasst (Zeitpunkt braucht keine Rolle mehr) |
| beispiel/reisen/stadtwochenende/plan/arten.yaml | MODIFY | Art `bahn`: ein Zeitpunkt-Merkmal mit `erinnern: true` und ein Text-Merkmal (Gleis) mit `bei: abfahrt` und `nach_buchung: true` (erfunden, als Beispielwert markiert) |
| beispiel/reisen/stadtwochenende/plan/routen.yaml | MODIFY | Werte dieser Merkmale an E-01 (Zeitpunkt mit Datum, Gleis) und E-02 (Zeitpunkt nur Uhrzeit, kein Gleis) |
| docs/design.md | MODIFY | Atome und Molekül Zeitleiste mit Heimat und Regeln in der Tabelle der Ebenen (ADR-0002, ADR-0003); Abschnitt zur Halteleiste nennt die gemeinsamen Atome |
| docs/ontologie.md | MODIFY | Form `zeitpunkt` ohne Rolle, Eigenschaften `erinnern` und `bei`, Hinweis „je Typ und Rolle einmal“ nur für abfahrt/ankunft |
| docs/funktionen/buchungen.md | MODIFY | die ab-Angabe einer Buchung steht jetzt in der Zeitleiste der Bewegung |
| docs/funktionen/erinnerungen.md | MODIFY | Erinnerung an Zeitpunkte des Dings |
| docs/funktionen/reiseseite.md | MODIFY | Zeitleiste der Bewegung, Zuordnung von Merkmalen zu Zeitpunkten |
| docs/konnektor.md | MODIFY | Parameter `erinnern` / `remind` und `bei` / `at` von `attribute_define` |
| docs/waechter.md | MODIFY | neue Erinnerung, Schlüssel, Doppelterinnerung |
| docs/adr/0007-elternbezug.md | MODIFY | Nachtrag im Verlauf (kein neues ADR, siehe Abschnitt ADR) |
| engine/tests/test_zeitleiste_bewegung.py | CREATE | Regeln, `bei`, Sortierung, Wächter, Kalender, Seitendaten, Konnektor an beiden Beispielreisen |
| engine/tests/test_typisierte_merkmale.py, test_routen.py, test_waechter.py, test_kalender.py, test_schreiben.py, test_konnektor.py, test_englisch_werte.py, test_seite.py, test_design.py, test_texte.py | MODIFY | angepasste und ergänzte Fälle (siehe Test Plan); `test_design.py`: Zeitleiste und Halteleiste nutzen die gemeinsamen Atome, alle Bausteine sind registriert |
| engine/tests/seiten_strecke_heimat.mjs | MODIFY | Browser-Prüfung der Zeitleiste (das Muster für die Heimat der Strecke gibt es dort schon) |
| engine/tests/seiten_halteleiste.mjs | CREATE | Browser-Gegenprobe der Halteleiste: gemessene Maße und Farben von Punkt, Linie, Zeit und Halt-Marke vor und nach dem Umbau gleich |

### Estimated Changes

- Files: rund 36 (Code, Texte, Beispieldaten, Doku und Tests zusammen)
- LoC: +700/-90 einschließlich Tests und Doku (Risiko mittel bis hoch: `streckeZeile` ist stark verzweigt, #619 darf nicht zurückkehren, die Halteleiste wird auf gemeinsame Atome umgestellt und darf sich nicht sichtbar ändern)

## Implementation Details

### a) Zeitpunkt ohne Rolle am Ding

- `lage_merkmale_falten` (routen.py ~349): Ein Merkmal vom Typ `zeitpunkt` ohne Rolle bleibt **Merkmal** (landet in `rest`, wird nicht gefaltet, kein Eintrag in `belegt`). Der Wert wird mit `lage_wert_gueltig("zeitpunkt", …)` geprüft; ein ungültiger Wert bleibt Fehler (`pruefung.routen.lage_wert`).
- `uhrzeit` ohne Rolle bleibt Fehler (`lage_rolle`); die Rollen `abfahrt` und `ankunft` (Bewegung) gelten weiter je Ding einmal (ADR-0007), weil Anschlussprüfung, Kalender und Karte sie lesen.
- Die Regel gilt für **jedes Ding** (eine Stelle im Code, ADR-0001 Frage 2). Mindestumfang und einzige Darstellung als Zeitleiste ist die **Bewegung**. An Aufenthalt und Unterkunft erscheint ein freier Zeitpunkt vorerst in der Merkmalliste (`wertNachTyp` formatiert ihn schon mit `zeitText`); eine Zeitleiste dort ist ein späteres Vorhaben.
- Der Text `pruefung.routen.lage_rolle` nennt `zeitpunkt` nicht mehr als rollenpflichtig, sondern nur `abfahrt` oder `ankunft` als mögliche Rollen.
- **Kein Formatwechsel:** Was heute ein Fehler ist (Zeitpunkt ohne Rolle am Ding), wird gültig; bestehende Reisen enthalten es nicht, es gibt nichts umzustellen. Daher kein Eintrag in `neu.py nachziehen` (CLAUDE.md, #250). Die Daten bleiben gespeichert, wie sie sind; nur die Darstellung wandert.

### b) Eigenschaft `erinnern`

- `DEF_FELDER` bekommt `erinnern`. Zulässig nur an Merkmalen vom Typ `zeitpunkt`; an jedem anderen Typ lehnt die Prüfung der Art-Definition (routen.py, Lesen von `arten.yaml`) und `merkmal_definieren` ab, mit eigenem Fehlertext aus dem Textkatalog. Es ist ein Schalter (keine Rolle), weil ein Ding mehrere Erinnerungen haben darf.
- `attribute_define`: Parameter `erinnern` (boolean), englisch `remind`; wie `nach_buchung` beim Anlegen und beim Ändern, mit Antwortsatz „erinnert jetzt / erinnert nicht mehr“. Ändert ein Aufruf nichts (gleicher Wert für `erinnern` bzw. `bei`), greift die vorhandene Ablehnung `schreiben.merkmal_definieren.12` („nichts daran soll sich ändern“); dafür zählen `erinnern` und `bei` in der Liste der Änderungen und in den gespeicherten Schlüsseln mit. Beim Ändern auf Typ ungleich `zeitpunkt` bei gesetztem `erinnern` Ablehnung. `attributes` und `show` zeigen „erinnert“ am Merkmal (wie die Zeile für `nach_buchung`, konnektor.py ~1356).
- **Wächter** (`waechter.py`, neben `buchungsfristen`): Für jedes Ding mit einem Zeitpunkt-Merkmal, dessen Definition `erinnern` trägt und dessen Wert ein **Datum** hat, wird wie bei der Buchungs-`ab` gemeldet, sobald der Tag des Zeitpunkts erreicht ist (Datum ≤ heute), einmal je Termin (`wiederholen: None`), gleicher Meldeweg und gleiche Statusregel (`verhalten(...)["fristen"]`, ab Status fest), Empfänger wie eine Buchung ohne `wer` (Organisator:innen). Schlüssel `zeit:<Ding>:<Merkmal>:<Wert>`; Ziel und Bezug sind die Kennung des Dings. Ein Wert ohne Datum (nur `HH:MM`) wird gezeigt, aber nicht erinnert.
- **Kalender** (`kalender.py`): ein Termin je erinnerndem Zeitpunkt mit Datum, gleiche Sorte und gleiche Form wie der Termin der Buchungs-`ab` (kein neuer Schalter im Konto nötig), UID `<Ding>-zeit-<Merkmal>`.
- **Keine Doppelmeldung:** Tragen eine Buchungs-`ab` (je Ding oder der Buchung, die das Ding betrifft) und ein erinnerndes Merkmal denselben Zeitpunkt am selben Ding (gleiches Datum und gleiche Uhrzeit), gewinnt die Buchung: die Erinnerung aus dem Merkmal und sein Kalendertermin entfallen. Das Buchungsfeld `ab` bleibt gültig und erinnert unverändert.
- Zeitpunkte werden nach dem geschriebenen Datum und der Uhrzeit verglichen (Ortszeit, wie in der Ontologie: die Software kennt keine Zeitzonen der Orte).

### c) Seite: Molekül „Zeitleiste“

- Neue Funktion `zeitLeiste(s, id)` in `vorlage.html` (Molekül), eingebaut in `streckeZeile` an der Heimat (`voll`) an der Stelle der kurzen Zeile.
- **Erscheinen:** nur an der Heimat und nur, wenn die Bewegung mindestens einen Zeitpunkt außer Abfahrt und Ankunft hat: ein Zeitpunkt-Merkmal ohne Rolle mit Wert, oder eine Buchungs-`ab` je Ding bzw. der Buchung des Dings (`buchungenBei`, `je_ding`). Sonst bleibt die kurze Zeile „ab … → an …“ unverändert (auch die Kompaktansichten ohne `voll`). Ein Merkmal mit `bei` allein löst keine Zeitleiste aus (Entscheidung: die Regel bleibt einfach; ohne Zeitleiste bleibt das Merkmal in der Merkmalliste).
- **Eine Schriftgröße:** Uhrzeit, Datum der Kopfzeile und abweichendes Datum haben dieselbe Größe (Schriftgröße der Seite für Fließtext, Token statt fester Pixelzahl). Abfahrt und Ankunft: `font-weight` der Bezeichnung fett, Punkt gefüllt in Blau; die Uhrzeit ist nicht größer und nicht fetter als die anderen.
- **Punkte:** feste `ab` und `an` (Bezeichnung „Abfahrt `<Ort von>`“, „Ankunft `<Ort nach>`“), übrige Zeitpunkte normal mit dem Namen des Merkmals, Buchungs-`ab` mit `ab_was` und dem Zusatz „aus der Buchung“. Marke „erinnert“ an jedem erinnernden Merkmal; an der Buchungs-`ab` ebenfalls, weil sie erinnert.
- **Reihenfolge:** nach Datum und Uhrzeit. `HH:MM` ohne Datum gilt am Tag der Strecke (Tag aus dem Plan, `PLAN_ANSICHT`, wie die Kopfzeile ihn heute schon bestimmt). Bei gleicher Zeit steht ein freier Punkt vor der Abfahrt und hinter der Ankunft. Ohne Tag der Strecke gilt das Datum der Abfahrt, wenn sie eins trägt. Ist der Tag der Fahrt so nicht bestimmbar, stehen Punkte mit Datum (etwa der Check-in am Vortag) vor denen ohne Datum; die ohne Datum folgen untereinander nach Uhrzeit (Gegenprüfung F002). Eine Ankunft ohne Datum, deren Uhrzeit nicht nach der Abfahrt liegt, gilt am Tag danach (Nachtfahrt, dieselbe Regel wie im Kalender; F001).
- **Datum bei der Uhrzeit:** Ein Punkt, dessen Datum vom Tag der Strecke abweicht, zeigt es mit Wochentag in der Uhrzeit-Spalte direkt unter der Uhrzeit (wie im Entwurf, `span.tag` als Block), fett, gleiche Größe. Die Uhrzeit-Spalte hat eine feste Breite, damit alle Bezeichnungen am selben linken Rand beginnen; am Handy (360 px) läuft nichts über.
- **Kopfzeile unter dem Titel:** bei vorhandener Zeitleiste nur das Datum der Fahrt (Format wie im Entwurf, „Fr 12.3.2027“), ohne Art-Name, fett, in der Größe der Uhrzeiten. Ist der Tag der Fahrt nicht bekannt (keine Plan-Ansicht, kein Datum), entfällt die Zeile. Die Art zeigt das Symbol im Titel (`artSym`, wie bisher). Keine Zeiten in der Kopfzeile (kein „ab … → an …“ doppelt, vgl. #619).
- **Eine Heimat (ADR-0003):** Zeitpunkt-Merkmale, die in der Zeitleiste stehen, erscheinen nicht noch einmal in `merkmalListe`; andere Merkmale (Flugnummer) bleiben in der Liste. `planungsTeil` und die Sichtbarkeit `nach_buchung` gelten für die Merkmalliste wie bisher; die Zeitleiste selbst steht immer oben sichtbar und nicht in „Aus der Planung“.
- **Buchungsblock:** `buchungBlock(b, ding)` zeigt die ab-Zeile („Online-Check-in ab …“) nicht mehr, wenn er an einer Bewegung steht, deren Zeitleiste sie trägt. An Unterkünften und anderen Dingen bleibt sie unverändert (Check-in-Ansicht #463).
- **Texte (ADR-0006):** alle sichtbaren Texte in `texte_de.py`, `texte_en.py` und der Pseudo-Sprache der Tests, zum Beispiel `seite.zeitleiste.name` (Ablauf), `seite.zeitleiste.abfahrt`, `seite.zeitleiste.ankunft`, `seite.zeitleiste.erinnert`, `seite.zeitleiste.aus_buchung`; dazu Fehler und Antworttexte der Definition (`erinnern` nur bei Typ Zeitpunkt, „erinnert jetzt / nicht mehr“, `bei` siehe d) und der Text der Wächter-Erinnerung. Die Ausnahmelisten in `test_texte.py` werden nicht länger.

### d) Zuordnung `bei:` eines Merkmals zu einem Zeitpunkt

- **Eigenschaft der Merkmal-Definition** `bei: <Schlüssel>` (Text, ein Schlüssel). Ziel ist entweder (1) der Schlüssel eines Merkmals vom Typ `zeitpunkt` derselben Art, oder (2) eine Rolle der festen Punkte: `abfahrt` oder `ankunft` (nur bei Arten der Grundform Bewegung). Fällt ein Schlüssel mit einem Rollennamen zusammen, gilt die Rolle. Das Ziel eines Merkmals kann selbst kein `bei` tragen (Zeitpunkt-Merkmale dürfen keins, siehe unten); mehrere Merkmale dürfen am selben Punkt stehen, sie erscheinen in der Reihenfolge ihrer Definition.
- **Regeln generisch (ADR-0001):** kein Merkmalname im Code, nur Typ und Eigenschaft. Geprüft an einer Stelle in `routen.py` beim Lesen von `arten.yaml` (nach dem Einlesen aller Merkmale der Art, damit ein Ziel auch weiter unten stehen darf) und im Schreibweg:
  - `bei` ist ein nichtleerer Text, sonst Fehler (Text aus dem Katalog, `pruefung.routen.bei`); er wird beim Lesen wie im Schreibweg klein geschrieben (`Abfahrt` gilt als `abfahrt`);
  - `bei` nicht an Merkmalen vom Typ `zeitpunkt` oder `uhrzeit` (sie sind selbst Punkte; `pruefung.routen.bei_typ`);
  - das Ziel muss existieren und eine der beiden Formen haben, sonst Ablehnung, die die gültigen Ziele der Art nennt (`pruefung.routen.bei_ziel`).
- **Schreibweg:** `attribute_define` bekommt den Parameter `bei` (englisch `at`, wie `nach_buchung`/`visible_after_booking` eine Eigenschaft am Merkmal). Anlegen und Ändern; ein leerer Text entfernt die Zuordnung (Antwortsatz „steht jetzt bei … / steht nicht mehr bei einem Zeitpunkt“). Wird der Typ eines Merkmals geändert, auf das andere `bei` zeigen, oder ein solches Ziel entfernt, lehnt der Schreibweg ab und nennt die abhängigen Merkmale. Beim Ändern des Typs eines Merkmals mit `bei` auf `zeitpunkt` oder `uhrzeit` ebenfalls Ablehnung. `attributes` und `show` zeigen die Zuordnung („steht bei <Name des Ziels>“).
- **Englischer Alias:** `PARAMETER` in `schnittstelle.py` bildet `bei` für alle Werkzeuge auf `booked_with` ab (Buchungsfeld „Gebucht bei“). Für `merkmal_definieren` kommt in `PARAMETER_JE_WERKZEUG` eine Ausnahme `bei -> at`; ein Test sichert, dass `booked_with` bei den Buchungswerkzeugen und `at` bei `attribute_define` bleibt und die deutsche Eingabe `bei` an beiden funktioniert.
- **Darstellung (ADR-0003, eine Heimat):** Ein Merkmal mit `bei` und Wert erscheint als **Zusatzzeile** (`leistenZusatz`: normale Größe, gedämpft) unter der Bezeichnung des Punkts, zu dem es gehört, und **nicht** mehr in der Merkmalliste. Gezeigt wird der Wert über das Atom `merkmalWert` (Typ, Herkunft, „ungeprüft“ wie in der Liste), ohne den Namen des Merkmals (wie im Entwurf: „Terminal 1, Schalter 20–28“). Der Wert verdrängt nie den Punkt: Sortierung und Marke ändern sich dadurch nicht.
- **Fallback:** Fehlt der Punkt in der Zeitleiste (das Zeitpunkt-Merkmal hat keinen Wert, die Bewegung hat keine Abfahrt oder Ankunft, oder es gibt keine Zeitleiste), bleibt das Merkmal in der Merkmalliste wie heute.
- **Sichtbarkeit `nach_buchung` bleibt maßgeblich:** Ein `bei`-Merkmal steht nur dann in der Zeitleiste, wenn es nach der heutigen Regel sichtbar wäre (nicht gebucht, oder `nach_buchung: true`). Wäre es nach der heutigen Regel nur in „Aus der Planung“, bleibt es dort (es steht dann in der Liste des zugeklappten Blocks, nicht in der Zeitleiste).
- **Kein Formatwechsel:** `bei` ist eine neue, optionale Eigenschaft der Merkmal-Definition; bestehende Reisen tragen sie nicht und ändern sich nicht, es gibt nichts umzustellen. Daher kein Eintrag in `neu.py nachziehen` (CLAUDE.md, #250).

### e) Atomic Design (ADR-0002, ausdrückliche Vorgabe des Product Owners)

- **Molekül aus gemeinsamen Atomen:** `zeitLeiste` und `halteLeiste` bauen ihre Leiste aus denselben Atomen: `leistenPunkt` (Punkt auf der Linie; Varianten leer und gefüllt), `leistenZeit` (Uhrzeit mit gleich breiten Ziffern), `leistenMarke` (kleine Pille; „erinnert“ der Zeitleiste und „Halt“ der Halteleiste, Farbe als Eigenschaft) und `leistenZusatz` (Zusatzzeile unter einer Bezeichnung; die Halteleiste nutzt sie, wo sie eine Zusatzzeile hat, sonst nur die Zeitleiste). Die Linie ist Sache des gemeinsamen Stils der Leiste (`leiste (CSS)` im Kopfkommentar, wie `etikett (CSS)`), nicht von zwei Stilblöcken.
- **Stile:** Die Stile von `ol.halte` und der Zeitleiste werden auf gemeinsame Atom-Klassen gestellt (Punkt, Linie, Ziffern, Marke) statt doppelter Stile; was nur eine der beiden Leisten braucht (die Uhrzeit-Spalte und der gefüllte Punkt der Zeitleiste; Halt und Fahrzeile der Halteleiste), bleibt an seinem Molekül. **Die Halteleiste ändert sich dabei sichtbar nicht:** der Browser-Test `seiten_halteleiste.mjs` misst vor dem Umbau Maße, Abstände und Farben von Punkt, Linie, Zeit und Halt-Marke (hell und dunkel, Handy und Rechner) und fordert nach dem Umbau dieselben Werte.
- **Die vier Stellen (Pflicht von ADR-0002):** Kopfkommentar „Bausteine nach Ebenen“ (Atome: `leistenPunkt`, `leistenZeit`, `leistenMarke`, `leistenZusatz`, `leiste (CSS)`; Moleküle: `zeitLeiste`), Stile ihrer Ebene, Bausteinseite (`ansichtBausteine` zeichnet jeden Baustein), `docs/design.md` (Tabelle der Ebenen, Abschnitt zur Halteleiste). Zeigt das Molekül eine Grundform (Zeitpunkt), steht es auch in `GRUNDFORMEN` und hat dort genau diese eine Heimat (ADR-0003): `bewegung` bekommt `zeitLeiste` in der Dichte „seite“ oder „zeile“, in der Tabelle der Grundformen in `docs/design.md` dieselbe Zelle.
- **Test in `test_design.py`:** (1) `zeitLeiste` ist als Molekül, ihre Atome sind als Atome im Kopfkommentar registriert, jeder Name ist eine Funktion der Vorlage und steht in `docs/design.md` und auf der Bausteinseite (die vorhandenen Tests prüfen das für alle Namen); (2) der Quelltext von `zeitLeiste` und von `halteLeiste` ruft `leistenPunkt` und `leistenZeit` auf (die gemeinsamen Atome) und zeichnet Punkt, Linie und Marke nicht selbst; (3) die Stile von `ol.halte` und `ol.zeit` enthalten keine eigene Punkt- und Linien-Deklaration mehr, sondern verweisen auf die gemeinsamen Klassen.

### Beispielreisen

- **Stadtwochenende:** E-01 und E-02 haben die Buchung B-01 mit `je_ding.ab` „Komfort-Check-in“; dort entsteht die Zeitleiste ohne Datenänderung. Zusätzlich bekommt die Art `bahn` (alles erfundene Beispielwerte, als solche markiert):
  - ein Merkmal vom Typ `zeitpunkt` mit `erinnern: true` (zum Beispiel „Fahrkarte freischalten ab“), an E-01 mit Datum des Vortags, an E-02 nur mit Uhrzeit (zeigt die Regel „ohne Datum nicht erinnern“);
  - ein Text-Merkmal „Gleis“ mit `bei: abfahrt` und `nach_buchung: true`, an E-01 mit Wert (steht als Zusatzzeile unter der Abfahrt), an E-02 ohne Wert (nichts zu zeigen).
- **Zuordnung an ein Zeitpunkt-Merkmal** (`bei: <Schlüssel eines Zeitpunkts>`) lässt sich mit der Reisedatenstruktur des Stadtwochenendes nicht sinnvoll darstellen, ohne die Beispielreise zu überladen. Sie wird in den Tests mit erfundenen Testdaten geprüft (eine Kopie der Beispielreise im Test, ein zweites Text-Merkmal mit `bei:` auf den erinnernden Zeitpunkt und eines ohne `nach_buchung`).
- **Beispielreise (Wanderung):** keine Änderung der Daten; ihre Bahnstrecke mit `abfahrt`/`ankunft` ohne weiteren Zeitpunkt behält die kurze Zeile und die heutige Kopfzeile. Sie ist Gegenprobe (ADR-0001 Frage 1) und wird in Tests und Abnahme mitgeprüft.

## Test Plan

### Automated Tests (TDD RED)

In `engine/tests/test_zeitleiste_bewegung.py` (und den ergänzten Dateien):

- [ ] Test 1: GIVEN ein Ding mit einem Zeitpunkt-Merkmal ohne Rolle (`HH:MM` und mit Datum) WHEN die Reise gelesen wird THEN bleibt es Merkmal (nicht gefaltet), kein Fehler; ein ungültiger Wert bleibt Fehler.
- [ ] Test 2: GIVEN ein `uhrzeit`-Merkmal ohne Rolle und ein zweites `zeitpunkt` mit Rolle `abfahrt` WHEN gelesen THEN `lage_rolle` für `uhrzeit`, `lage_doppelt` für die zweite Abfahrt (ADR-0007 bleibt); `test_typisierte_merkmale.py` angepasst.
- [ ] Test 3: GIVEN `erinnern: true` an einem Merkmal vom Typ `text` WHEN die Art gelesen oder `attribute_define` mit `remind` aufgerufen wird THEN Ablehnung mit Fehlertext aus dem Textkatalog (in de, en und Pseudo-Sprache vorhanden).
- [ ] Test 4: GIVEN `attribute_define` mit `remind` (englisch) und `erinnern` (deutsch) an einem Zeitpunkt-Merkmal WHEN geschrieben und `attributes`/`show` gelesen werden THEN ist `erinnern` gespeichert und sichtbar; dasselbe Ändern ohne Wirkung wird mit `schreiben.merkmal_definieren.12` abgelehnt.
- [ ] Test 5: GIVEN ein erinnerndes Zeitpunkt-Merkmal mit Datum an E-01 (Stadtwochenende) und Reisestatus fest WHEN der Wächter an dem Tag läuft THEN genau eine Erinnerung mit Schlüssel `zeit:E-01:<Merkmal>:<Wert>`; beim zweiten Lauf keine neue (einmal je Termin).
- [ ] Test 6: GIVEN dasselbe Merkmal an E-02 nur mit `HH:MM` WHEN der Wächter und der Kalender laufen THEN keine Erinnerung und kein Kalendertermin, die Seite zeigt den Punkt aber.
- [ ] Test 7: GIVEN eine Buchungs-`ab` und ein erinnerndes Merkmal mit demselben Datum und derselben Uhrzeit am selben Ding WHEN Wächter und Kalender laufen THEN nur eine Erinnerung (die der Buchung) und ein Kalendertermin; bei verschiedener Zeit beide.
- [ ] Test 8: GIVEN erinnernde Zeitpunkte WHEN der Kalender gebaut wird THEN je ein Termin mit eindeutiger UID `<Ding>-zeit-<Merkmal>`, die UIDs der Buchungs-Termine bleiben unverändert.
- [ ] Test 9: GIVEN die gebauten Seitendaten des Stadtwochenendes WHEN die Zeitpunkte von E-01 aufbereitet werden THEN stehen sie in der Reihenfolge Merkmal (Vortag), Buchungs-`ab` „Komfort-Check-in“, Abfahrt, Ankunft; an E-02 (Fahrt 14.3.) steht die Buchungs-`ab` (Vortag, 13.3. 17:40) vorn, dann das Merkmal ohne Datum am Tag der Fahrt vor der Abfahrt, dann Ankunft.
- [ ] Test 10: GIVEN die Bahnstrecke der Beispielreise (Wanderung) ohne weitere Zeitpunkte WHEN die Seite gebaut wird THEN erscheint keine Zeitleiste, die kurze Zeile „ab … → an …“ und die heutige Kopfzeile „Art · Datum · ab … → an …“ bleiben unverändert (Gegenprobe, Risiko #619).
- [ ] Test 11: GIVEN die Seite der Bewegung mit Zeitleiste WHEN der Browser sie lädt (`seiten_strecke_heimat.mjs`, Stadtwochenende E-01 und E-02, Handy- und Rechnerbreite) THEN steht die Zeitleiste einmal, in zeitlicher Reihenfolge (E-01: Merkmal, Buchungs-`ab`, Abfahrt, Ankunft; E-02: Buchungs-`ab` am Vortag, Merkmal, Abfahrt, Ankunft); die berechnete Schriftgröße aller Uhrzeiten, des Datums der Kopfzeile und eines abweichenden Datums ist gleich; Abfahrt und Ankunft haben fetten Namen und gefüllten Punkt, die übrigen Punkte sind leer und nicht fett; die Marke „erinnert“ steht am erinnernden Punkt; ein abweichendes Datum steht fett in der Uhrzeit-Spalte direkt unter der Uhrzeit, gleiche Schriftgröße; die Kopfzeile zeigt nur das Datum, keinen Art-Namen und keine Uhrzeit; `merkmalListe` enthält die Zeitpunkte nicht noch einmal; der Buchungsblock zeigt keine ab-Zeile; bei 360 px läuft nichts über.
- [ ] Test 12: GIVEN eine Unterkunft oder ein Aufenthalt mit Buchungs-`ab` WHEN `buchungBlock` gezeichnet wird THEN bleibt die ab-Zeile unverändert (nur Bewegungen mit Zeitleiste verlieren sie).
- [ ] Test 13: GIVEN die Texte WHEN `test_texte.py` läuft THEN sind alle neuen Schlüssel in de, en und der Pseudo-Sprache vorhanden, und die Ausnahmelisten sind nicht länger.
- [ ] Test 14: GIVEN beide Beispielreisen vor und nach dem Bau WHEN die Reisedaten gelesen werden THEN sind außer den neuen Beispielwerten keine Daten verändert und `neu.py nachziehen` ändert nichts (kein Formatwechsel, weder für `erinnern` noch für `bei`).
- [ ] Test 15 (`bei`, Lesen): GIVEN eine `arten.yaml` mit einem Text-Merkmal `bei: abfahrt` bzw. `bei: <Schlüssel eines Zeitpunkt-Merkmals>` (auch wenn das Ziel weiter unten steht) WHEN die Art gelesen wird THEN ist `bei` übernommen und kein Fehler.
- [ ] Test 16 (`bei`, Ablehnung): GIVEN `bei` an einem Merkmal vom Typ `zeitpunkt` oder `uhrzeit`, ein Ziel, das es nicht gibt, ein Ziel vom Typ `text`, `bei: abfahrt` an einer Art ohne Grundform Bewegung, oder ein leerer/nicht-textlicher Wert WHEN die Art gelesen oder `attribute_define` aufgerufen wird THEN Ablehnung mit Text aus dem Katalog (de, en, Pseudo-Sprache), der die gültigen Ziele nennt.
- [ ] Test 17 (`bei`, Konnektor): GIVEN `attribute_define` mit `at` (englisch) und `bei` (deutsch) WHEN geschrieben und `attributes`/`show` gelesen werden THEN ist die Zuordnung gespeichert und sichtbar („steht bei …“, de und en); ein leerer Text entfernt sie; das Ändern des Typs eines Ziels, auf das ein anderes Merkmal zeigt, wird abgelehnt; `booked_with` bleibt der englische Name von `bei` an den Buchungswerkzeugen (`test_englisch_werte.py`, `test_konnektor.py`).
- [ ] Test 18 (`bei`, Seite): GIVEN die Seite der Bewegung E-01 des Stadtwochenendes WHEN der Browser sie lädt THEN steht der Wert des Gleis-Merkmals als Zusatzzeile (normale Größe, gedämpfte Farbe) unter der Bezeichnung „Abfahrt …“ und nicht in der Merkmalliste; mit Testdaten (Merkmal `bei:` auf den erinnernden Zeitpunkt) steht der Wert unter diesem Punkt.
- [ ] Test 19 (`bei`, Fallback): GIVEN ein `bei`-Merkmal, dessen Ziel-Zeitpunkt keinen Wert hat, oder eine Bewegung ohne Zeitleiste WHEN die Seite gebaut wird THEN steht das Merkmal in der Merkmalliste wie heute und nicht in der Zeitleiste.
- [ ] Test 20 (`bei`, `nach_buchung`): GIVEN eine gebuchte Bewegung und zwei `bei`-Merkmale, eines mit `nach_buchung: true`, eines ohne WHEN die Seite gebaut wird THEN steht das erste als Zusatzzeile in der Zeitleiste, das zweite nur in „Aus der Planung“; ungebucht stehen beide in der Zeitleiste.
- [ ] Test 21 (Atomic Design): GIVEN `engine/vorlage.html` WHEN `test_design.py` läuft THEN sind `zeitLeiste` (Molekül) und die Atome `leistenPunkt`, `leistenZeit`, `leistenMarke`, `leistenZusatz` im Kopfkommentar, in `docs/design.md` und auf der Bausteinseite registriert; `zeitLeiste` und `halteLeiste` rufen `leistenPunkt` und `leistenZeit` auf; die Stile enthalten Punkt und Linie nur einmal (gemeinsame Klassen); `GRUNDFORMEN` und die Tabelle in `docs/design.md` nennen für `bewegung` dasselbe.
- [ ] Test 22 (Halteleiste unverändert): GIVEN die Seite einer Strecke mit Zwischenstopps (Beispielreise, Wanderung) WHEN der Browser sie lädt (`seiten_halteleiste.mjs`, hell und dunkel, Handy und Rechner) THEN stimmen gemessene Maße, Abstände und Farben von Punkt, Linie, Zeit und Halt-Marke der Halteleiste mit den vor dem Umbau gemessenen Werten überein.

### Vertrag der Tests (TDD RED, 24.11.2026)

Festgelegt in `engine/tests/test_zeitleiste_bewegung.py`, `seiten_zeitleiste_665.mjs`, `seiten_halteleiste.mjs` und `halteleiste_vorher.json` (Maße der Halteleiste vor dem Umbau):

- **Freier Zeitpunkt:** neu gültig ist der Wert mit Typ am Ding (`{typ: zeitpunkt, wert: …}` ohne Rolle, wie abfahrt/ankunft geschrieben); ein Merkmal der Art vom Typ `zeitpunkt` ist schon heute gültig.
- **Beispielreise Stadtwochenende, Art `bahn`:** `freischalten` (Name „Fahrkarte freischalten ab“, Typ `zeitpunkt`, `erinnern: true`; E-01 `2027-03-11T<früher als 09:10>`, E-02 nur Uhrzeit vor 17:40) und `gleis` (Typ `text`, `bei: abfahrt`, `nach_buchung: true`; Wert nur an E-01); Quellen mit „Beispiel“.
- **Seitendaten:** `route.strecken.<ID>.zeitleiste` = Liste in zeitlicher Reihenfolge, je Punkt `art` (`merkmal` | `buchung` | `abfahrt` | `ankunft`), `merkmal` (Schlüssel oder fehlt), `zeit` (`HH:MM`), `datum` (`JJJJ-MM-TT`, ohne eigenes Datum der Tag der Strecke), `erinnert` (bool, Buchungs-`ab` ist erinnert), `bei` (Schlüssel der Merkmale mit Wert, die an diesem Punkt stehen; die Sichtbarkeit `nach_buchung` entscheidet die Seite), am Punkt `buchung` zusätzlich `buchung` (B-…) und `was` (`ab_was`). Ohne Punkt außer abfahrt/ankunft fehlt `zeitleiste` oder ist leer.
- **Seite:** `ol.zeit` im Element der Heimat; je Punkt `li[data-art][data-merkmal]` mit `.leisten-punkt` (gefüllt: Klasse `voll`), `.leisten-zeit` (abweichendes Datum als `.tag` darin, unter der Uhrzeit), `.leisten-name`, `.leisten-marke`, `.leisten-zusatz`; Kopfzeile mit Zeitleiste `.zeitleiste-kopf`.
- **Wächter:** Schlüssel `zeit:<Ding>:<Merkmal>:<Wert>`, `ziel`/`bezug` = Ding, `art` = erinnerung, Text nennt Namen des Merkmals und Uhrzeit. **Kalender:** Sorte `buchungen`, UID `<Ding>-zeit-<Merkmal>`, `tag` = Datum, Titel nennt den Namen des Merkmals.
- **Textschlüssel:** siehe `NEUE_TEXTE` im Test (u. a. `pruefung.routen.erinnern`, `…erinnern_typ`, `…bei`, `…bei_typ`, `…bei_ziel`; `schreiben.merkmal_definieren.erinnern_typ`, `…bei_typ`, `…bei_ziel`, `…bei_abhaengig`; `schreiben.antwort.merkmal.erinnern_an`/`_aus`, `.bei`/`.bei_aus`; `konnektor.merkmale.erinnern`, `.bei`).
- **Atomic Design:** `halteLeiste` zeichnet Punkt und Zeit nicht mehr selbst (`hl-p`, `hl-zeit` nicht in ihrem Rumpf), keine Stile `ol.halte>li::before` / `ol.zeit>li::before` und kein `.hl-p{`; `leiste (CSS)` im Kopfkommentar.

## Acceptance Criteria

- **AC-1:** Given ein Ding mit einem Zeitpunkt-Merkmal ohne Rolle / When die Reise gelesen wird / Then ist es gültig und bleibt Merkmal; `uhrzeit` ohne Rolle bleibt ein Fehler, abfahrt und ankunft gelten je einmal.
- **AC-2:** Given eine Reise, die `erinnern` an einem Zeitpunkt-Merkmal setzt (Konnektor `remind` oder `erinnern`) / When sie gespeichert und gelesen wird / Then ist die Eigenschaft sichtbar in `attributes` und `show`; an anderen Typen wird sie mit Text aus dem Katalog abgelehnt.
- **AC-3:** Given ein erinnernder Zeitpunkt mit Datum bei Status fest / When der Wächter läuft / Then kommt genau eine Erinnerung auf dem gleichen Meldeweg wie die Buchungs-`ab` und der Kalender trägt genau einen Termin mit eigener UID; ohne Datum wird nicht erinnert.
- **AC-4:** Given eine Buchungs-`ab` und ein erinnerndes Merkmal mit gleichem Zeitpunkt am selben Ding / When Wächter und Kalender laufen / Then gibt es nur eine Erinnerung und einen Kalendertermin.
- **AC-5:** Given eine Bewegung mit mindestens einem Zeitpunkt außer Abfahrt und Ankunft (Merkmal oder Buchungs-`ab`) / When ihre Heimat gezeigt wird / Then erscheint die Zeitleiste in zeitlicher Reihenfolge (freier Punkt bei gleicher Zeit vor der Abfahrt bzw. hinter der Ankunft).
- **AC-6:** Given dieselbe Zeitleiste / When ihre Schrift gemessen wird / Then haben alle Uhrzeiten und Daten (auch das Datum der Kopfzeile und ein abweichendes Datum) dieselbe Schriftgröße; Abfahrt und Ankunft unterscheiden sich nur durch fetten Namen und gefüllten Punkt.
- **AC-7:** Given eine Bewegung mit Zeitleiste / When ihre Kopfzeile unter dem Titel gezeigt wird / Then steht dort, sofern der Tag der Fahrt bekannt ist, nur das Datum der Fahrt (fett, Größe der Uhrzeiten) ohne Art-Name und ohne Uhrzeiten, sonst entfällt die Zeile; ein abweichendes Datum eines Punkts steht fett direkt unter seiner Uhrzeit in derselben Spalte.
- **AC-8:** Given dieselbe Bewegung / When die Heimat gezeigt wird / Then steht jeder Zeitpunkt nur in der Zeitleiste (nicht auch in der Merkmalliste), andere Merkmale bleiben in der Liste, und der Buchungsblock zeigt keine ab-Zeile; an Unterkünften bleibt die ab-Zeile.
- **AC-9:** Given eine Bewegung ohne weitere Zeitpunkte (Bahnstrecke der Beispielreise) / When ihre Heimat gezeigt wird / Then bleibt die kurze Zeile „ab … → an …“ und die heutige Kopfzeile „Art · Datum · ab … → an …“ unverändert.
- **AC-10:** Given ein Merkmal mit `bei: <Schlüssel>` (Zeitpunkt-Merkmal derselben Art, oder `abfahrt`/`ankunft`) / When die Reise gelesen oder `attribute_define` mit `at` oder `bei` aufgerufen wird / Then ist die Zuordnung gespeichert und in `attributes` und `show` sichtbar; an Zeitpunkt/Uhrzeit-Merkmalen und bei unbekanntem Ziel wird sie mit Text aus dem Katalog (de und en) abgelehnt.
- **AC-11:** Given ein Merkmal mit `bei` und Wert an einer Bewegung mit Zeitleiste / When ihre Heimat gezeigt wird / Then steht sein Wert als Zusatzzeile unter dem zugehörigen Punkt und nicht in der Merkmalliste; fehlt der Punkt oder die Zeitleiste, steht es in der Merkmalliste wie heute; die Sichtbarkeit `nach_buchung` bleibt maßgeblich.
- **AC-12:** Given der Quelltext der Vorlage / When `test_design.py` läuft / Then sind Molekül `zeitLeiste` und die gemeinsamen Atome an den vier Stellen (Kopfkommentar, Stile, Bausteinseite, `docs/design.md`) registriert, `zeitLeiste` und `halteLeiste` nutzen dieselben Atome, und die Halteleiste sieht im Browser-Vergleich unverändert aus.
- **AC-13:** Given beide Beispielreisen / When Seite, Wächter, Kalender und Konnektor geprüft werden / Then zeigen Seite und Konnektor `show` an E-01 dieselben Zeitpunkte, Wächter und Kalender melden je erinnerndem Zeitpunkt mit Datum genau einen Termin (Tests 5–7, 11), und die gespeicherten Reisedaten sind außer den neuen Beispielwerten unverändert; `neu.py nachziehen` ändert nichts (Test 14).
- **AC-14:** Given die vollständige Testsuite / When `engine/.venv/bin/python -m pytest -q engine/tests -n 3` läuft / Then ist sie grün, einschließlich `test_texte.py`, `test_design.py`, des Browser-Tests der Heimat der Strecke, der Gegenprobe der Halteleiste und des Protokolltests ohne Pfade.

## Definition of Done

- [ ] Alle Tests in `engine/tests/test_zeitleiste_bewegung.py` und den ergänzten Dateien grün, volle Testsuite grün (lokal und CI).
- [ ] Abnahme an beiden Beispielreisen: Seite (Handy und Rechner, hell und dunkel; Halteleiste der Wanderung unverändert), Wächter, Kalender und Konnektor (nur über den Testzugang `frieda-test`, nie über das Konto des Product Owners).
- [ ] Entwurf (Version 3) und Spec dem Product Owner vorgelegt und freigegeben; Inhalt des Entwurfs und seiner Änderungen steht als Kommentar im Issue #665.
- [ ] Atomic Design an den vier Stellen nachgezogen (Kopfkommentar, Stile, Bausteinseite, `docs/design.md`, bei gezeigter Grundform auch `GRUNDFORMEN`), `test_design.py` grün.
- [ ] Öffentliche Doku nachgezogen (siehe Affected Files); Nachtrag in ADR-0007 (freie Zeitpunkte, `erinnern`, `bei`).
- [ ] Ausgeliefert und auf der Instanz veröffentlicht; Folge-Issue nur für die Vorlage Art `flug` (Online-Check-in, Gepäckabgabe, Boarding, Terminal, `bei` auf Abfahrt bzw. Gepäckabgabe) angelegt; Issue #665 erst danach geschlossen, soweit es nach diesem Umfang vollständig erledigt ist, sonst bleibt es für die Vorlage offen.

## Prüfstelle ADR-0001

1 ja (Funktion ist an Wanderung und Stadtwochenende durchzuspielen; keine Flug-Sonderlogik, die Zeitleiste folgt Typ und Rolle, `bei` verweist auf einen Schlüssel oder eine Rolle, nicht auf einen Namen). 2 ja (kein Merkmalname im Code, nur Typ `zeitpunkt` und die Eigenschaften `erinnern` und `bei`; die Rollennamen `abfahrt`/`ankunft` sind schon Teil der Ontologie; Arten und Merkmale gehören der Reise). 3 ja (Wächter und Kalender rechnen und melden nur). 4 ja (`attribute_define` mit `erinnern`/`remind` und `bei`/`at`, `show`/`attributes`, `docs/konnektor.md`). 5 ja (jedes Zeitpunkt-Merkmal ist eine Aussage mit Herkunft, die bestehende Prüfung bleibt; ein `bei`-Merkmal zeigt seine Herkunft über `merkmalWert` wie in der Liste). 6 nicht berührt. 7 ja (keine neue ID, nichts gelöscht, Daten bleiben unverändert; `bei` und `erinnern` sind optionale Eigenschaften ohne Formatwechsel). 8 Rundgang nötig (Seite, offline wie bisher, Browser-Tests). 9 ja (Inhalte entstehen weiter im AI-Client). 10 siehe Doku-Liste und ADR-0007.

## Architektur-Entscheidung (ADR)

- **ADR-Nr.:** keine neue; Nachtrag in ADR-0007 (Verlauf)
- **Rationale:** Die Änderung bleibt im Rahmen von ADR-0007 (typisierte Merkmale statt Sonderfelder): `zeitpunkt` ohne Rolle ist ein freies Merkmal, und `erinnern` und `bei` sind weitere Eigenschaften der Merkmal-Definition wie `nach_buchung` oder `lang`. Die Regel „je Typ und Rolle einmal“ gilt weiter für abfahrt und ankunft. Der Nachtrag hält fest: freie Zeitpunkte sind zulässig, `erinnern` gilt nur für Typ `zeitpunkt`, `bei` ordnet ein Merkmal einem Zeitpunkt derselben Art oder einer festen Rolle (abfahrt, ankunft) zu und gilt nicht an Zeitpunkten selbst, Wächter und Kalender lesen `erinnern`, und die Zeitleiste ist Darstellung ohne Datenumzug. Das Molekül Zeitleiste folgt ADR-0002 (gemeinsame Atome mit der Halteleiste) und ADR-0003 (jeder Zeitpunkt und jedes `bei`-Merkmal hat genau eine Heimat auf der Seite). Eine eigene Entscheidung (neue Grundform, neuer Kern) ist nicht nötig.

## Out of Scope

- Vorlage Art `flug` in `engine/artvorlagen` (ADR-0011) mit Online-Check-in, Gepäckabgabe, Boarding und Terminal (Folge-Issue; die Zuordnung `bei:` dafür kommt in diesem Auftrag).
- Neue Kopfzeile (nur Datum) ohne Zeitleiste: Ohne Zeitleiste bleibt die heutige Kopfzeile „Art · Datum · ab … → an …“ unverändert (bewusst, Risiko #619 klein halten).
- Zeitleiste an Aufenthalt und Unterkunft (dort erscheinen freie Zeitpunkte vorerst in der Merkmalliste; `bei` auf `beginn`/`ende` ist nicht vorgesehen).
- Auslösen der Zeitleiste allein durch ein `bei`-Merkmal.
- Umzug der Buchungsfelder `ab`/`ab_was` in Merkmale (sie bleiben gültig und erinnern unverändert).

## Changelog

- 2026-11-24: Initial spec created
- 2026-11-24: Änderungen des PO am Entwurf eingearbeitet (Schriftgröße, Kopfzeile, bei:, Atomic Design)
- 2026-11-24: Testvertrag E-02 an Beispieldaten angepasst (Fahrt 14.3., Buchungs-ab 13.3.), test_buchung_zeitraum auf AC-7/AC-8 nachgezogen, Test 6 prüft gezielt E-02.
- 2026-11-24: Gegenprüfung: Nachtankunft ohne Datum am Tag danach (F001), Fahrt ohne Tag: Punkte mit Datum vor denen ohne (F002), englische Texte nennen at und remind (F003), bei beim Lesen klein geschrieben wie im Schreibweg (F004).
