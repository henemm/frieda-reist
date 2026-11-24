# Context: fix-665-zeitleiste (#665)

## Request Summary
Eine Bewegung (Beispiel Flug) soll ihren Ablauf als chronologische Zeitleiste zeigen: Online-Check-in ab, Gepäckabgabe bis, Boarding, Abflug (groß, mit Terminal), Ankunft (groß). Zur Buchung gehört nur das Geschäftliche (Nummer, Status, Preis, Zahlung, Reisende, Tarif, Beleg). Der Online-Check-in am Ding soll weiter erinnern wie bisher das Feld `ab` der Buchung. Die Lösung muss generisch bleiben (ADR-0001: die Software kennt nur Grundformen und Formen von Merkmalen).

## Related Files
| File | Relevance |
|------|-----------|
| engine/routen.py:229-234, 349-375 | Formen `uhrzeit`/`zeitpunkt`; feste Felder `ab`/`an` der Bewegung (Rollen abfahrt/ankunft) |
| engine/routen.py:61-67, 100 | Buchungsfelder (`ab`, `ab_was`, `frist`, `frist_was`, `je_ding`), `buchung_termine` |
| engine/routen.py:1599-1622, 2109 | Art-Merkmale mit typ, Liste in Definitionsreihenfolge an die Seite |
| engine/vorlage.html:2080-2121 | `streckeZeile`: kleine graue Zeile ab → an, `planungsTeil`, `nach_buchung` |
| engine/vorlage.html:2001, 310-316 | `halteLeiste` (ol.halte), vorhandene senkrechte Zeitleiste, Vorbild |
| engine/vorlage.html:2471-2528 | `buchungBlock`: ab-Zeile („Online-Check-in ab …“) prominent |
| engine/vorlage.html:2631-2710 | `wertNachTyp`, `merkmalWert`, `merkmalListe` |
| engine/waechter.py:225-264 | `buchungsfristen`: Erinnerung aus Buchung `ab`/`frist`/`storno_bis` |
| engine/kalender.py:133-197 | Kalender aus Strecke ab/an und Buchung ab |
| engine/artvorlagen/de.yaml:34-41, en.yaml | Vorlage Art `flug` hat nur `flugnummer` |
| engine/schreiben.py:740-885 | `merkmal_definieren` (attribute_define), gespeicherte Schlüssel |
| engine/texte_*.py | sichtbare Texte (seite.strecke.*) |
| beispiel/reisen/stadtwochenende/plan/routen.yaml | Bahn E-01/E-02 mit Buchung B-01, je_ding ab „Komfort-Check-in“ |
| beispiel/reisen/beispielreise/plan/routen.yaml:73 | Bahnstrecke mit abfahrt/ankunft |

## Existing Patterns
- Art-Merkmale der Form `zeitpunkt`/`uhrzeit` sind erlaubt (mehrere je Ding), werden per `zeitText` formatiert, aber in Definitionsreihenfolge in `merkmalListe` gezeigt.
- Feste Zeitfelder der Grundform (`ab`/`an`, `beginn`/`ende`) stehen nur in der kleinen Kopfzeile.
- `halteLeiste` zeigt schon eine Folge mit Zeiten als senkrechte Punktleiste (Design #509).
- `nach_buchung` entscheidet, was nach der Buchung über dem Buchungsblock sichtbar bleibt.
- Erinnerungen kommen nur aus Buchungsfeldern (`buchung_termine`), nicht aus Merkmalen.

## Dependencies
- Upstream: Merkmal-Typen in routen.py, Texte, `zeitText` in der Vorlage.
- Downstream: Seite (vorlage.html), Wächter, Kalender, Konnektor (attribute_define, show), Doku design.md, funktionen/buchungen.md, ontologie.md, ADR-0011-Vorlagen.

## Existing Specs
- docs/specs/oberflaeche/uhrzeit-doppelt-619.md (Uhrzeit doppelt)
- docs/specs/oberflaeche/klappen-zugeklappt-632.md (Einzelheiten zugeklappt)

## Risks & Considerations
- Kern: keine Flug-Sonderlogik; die Zeitleiste muss für jede Bewegung (und ggf. jeden Aufenthalt) aus Formen ableitbar sein: alle zeitlichen Merkmale plus feste ab/an, chronologisch.
- `zeitpunkt` als HH:MM ohne Datum vs. mit Datum: die Sortierung braucht einen Tagesbezug (Check-in am Vortag).
- Erinnerung aus Merkmal: neues Verhalten im Wächter; braucht ein generisches Kennzeichen (Rolle oder Eigenschaft), sonst erinnert jedes Zeit-Merkmal.
- Buchungsfeld `ab` bleibt gültig (keine Handarbeit, #250); Darstellung verschieben statt Daten umziehen, oder Umzug über `nachziehen`.
- Terminal/Check-in-Bereich: Zuordnung eines Text-Merkmals zur Abfahrt braucht ein generisches Mittel.
- Erst zeigen, dann bauen: Entwurf als Artefakt vor der Umsetzung (#436).
- Beide Beispielreisen prüfen (Bahn im Stadtwochenende).

## Analysis

### Type
Feature (Wunsch aus der Claude-App)

### Befund vorab
`lage_merkmale_falten` (engine/routen.py:349-375) lehnt `zeitpunkt`/`uhrzeit` ohne Rolle am Ding ab (`pruefung.routen.lage_rolle`); erlaubt sind nur abfahrt/ankunft bzw. beginn/ende, je einmal. Freie Zeit-Merkmale (Online-Check-in, Gepäckabgabe, Boarding) am Ding sind heute also nicht zulässig; der Workaround der meldenden Person läuft vermutlich über Text-Merkmale. Damit ist #665 auch eine Änderung der Datenregeln, nicht nur der Darstellung.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/routen.py | MODIFY | `zeitpunkt` ohne Rolle am Ding zulassen (bleibt Merkmal, kein Falten); `erinnern` in `DEF_FELDER`; Zeitpunkte des Dings für die Seite aufbereiten (Tagesbezug) |
| engine/schreiben.py | MODIFY | `merkmal_definieren`: Eigenschaft `erinnern` (nur Typ `zeitpunkt`), speichern (Zeile ~885) |
| engine/konnektor.py, engine/schnittstelle.py | MODIFY | Parameter `erinnern` (englisch `remind`) an attribute_define, Anzeige in show/attributes |
| engine/waechter.py | MODIFY | neue Erinnerung aus Zeit-Merkmal mit `erinnern` neben `buchungsfristen`, Schlüssel `zeit:<ID>:<merkmal>:<wert>`, einmal je Termin |
| engine/kalender.py | MODIFY | Kalendereintrag je erinnerndem Zeit-Merkmal, eindeutige UID `<ID>-<merkmal>` |
| engine/vorlage.html | MODIFY | neuer Baustein Zeitleiste der Bewegung (Vorbild `halteLeiste`): ab/an groß, übrige Zeitpunkte und Buchungs-`ab` (je Ding) chronologisch; `buchungBlock` ohne ab-Zeile; Kopfzeile ohne doppelte Zeiten; Bausteinseite |
| engine/texte_de.py, engine/texte_en.py | MODIFY | Texte der Zeitleiste, `erinnern`, Fehlertexte, Wächter-Erinnerung |
| engine/artvorlagen/de.yaml, en.yaml | MODIFY (Schritt 2) | Art flug: Zeit-Merkmale ohne Werte (Online-Check-in mit erinnern, Gepäckabgabe, Boarding, Terminal) |
| beispiel/reisen/stadtwochenende/plan/* | MODIFY | Bahn: ein freies Zeit-Merkmal als Beispielwert, damit Zeitleiste und Erinnerung an einer Beispielreise geprüft werden |
| docs/design.md, docs/ontologie.md, docs/funktionen/buchungen.md, docs/funktionen/erinnerungen.md, docs/funktionen/reiseseite.md, docs/waechter.md, docs/konnektor.md | MODIFY | Baustein, Form `erinnern`, freie Zeitpunkte, Erinnerung aus dem Ding |
| engine/tests/test_routen.py, test_typisierte_merkmale.py, test_waechter.py, test_kalender.py, test_schreiben.py, test_seite.py, test_design.py, browser seiten_strecke_heimat.mjs | MODIFY | Zulassung, erinnern, Wächter, Kalender, Seite |
| engine/tests/test_zeitleiste_bewegung.py | CREATE | Sortierung inkl. Vortag, Buchungs-ab als Punkt, keine leere Leiste, keine Doppel-Erinnerung |

### Scope Assessment
- Files: ~15 Code/Doku + Tests
- Estimated LoC: Schritt 1 +450/-50 (inkl. Tests), Schritt 2 +100–150
- Risk Level: MEDIUM (streckeZeile stark verzweigt, #619 Uhrzeit doppelt; Wächter/Kalender neue Termine; neue Datenregel)

### Technical Approach
Generisch nach ADR-0001 (kein Merkmalname im Code), zwei Schritte:
1. a) Freie `zeitpunkt`-Merkmale am Ding zulassen (bleiben Merkmal; `uhrzeit` ohne Rolle bleibt Fehler). Heute Fehler, künftig gültig: kein Bruch, keine Umstellung in `neu.py` nötig.
   b) Eigenschaft `erinnern: true` an der Definition (Schalter, keine Rolle, weil ein Ding mehrere Erinnerungen braucht). Nur für `zeitpunkt`; der Wert braucht ein Datum, sonst erinnert er nicht (Check-in am Vortag braucht ohnehin ein Datum). Wächter und Kalender lesen sie wie das Buchungsfeld `ab`.
   c) Seite: Zeitleiste der Bewegung = feste ab/an (groß) + alle Zeitpunkt-Merkmale + Buchungs-`ab` (je Ding), chronologisch; HH:MM gilt am Tag der Strecke. Buchungsblock zeigt nur noch Geschäftliches. Buchungsfeld `ab` bleibt gültig und erinnert unverändert (nur Darstellung wandert, keine Datenumstellung).
   Terminal bleibt zunächst als Text-Merkmal (`nach_buchung`) in der Merkmalliste.
2. Zuordnung eines Merkmals zu einem Zeitpunkt (`bei: <Schlüssel>`, z. B. Terminal am Abflug) und Vorlage Art flug, nach Rückmeldung.
Reihenfolge: a → b → c; c erst nach Entwurf als Artefakt und Freigabe (#436).
Doppel-Erinnerung vermeiden: der Wächter liest Buchungs-`ab` und Merkmal getrennt; tragen beide denselben Termin, wird mit gleichem Schlüssel (Ding + Datum/Zeit) nur einmal gemeldet.

### Dependencies
- Upstream: TYPEN/TYP_FELD/LAGE_TYPEN, ZEIT_MUSTER/zeitpunkt(), DEF_FELDER, rolle_pruefen, zeitText/wertNachTyp, halteLeiste.
- Downstream: Wächter (buchungsfristen, systemd-Timer), Kalender-Abo, Konnektor (attribute_define, show), Seite, Doku.
- ADR-0007 (je Typ+Rolle einmal) bleibt für abfahrt/ankunft; ADR-0011 (Vorlagen ohne Werte) für Schritt 2.

### Open Questions (Produktentscheidungen, im Entwurf zur Freigabe vorlegen)
- [ ] Gestaltung der Zeitleiste: was groß, Datum mit Wochentag je Punkt.
- [ ] Wandert das Buchungs-`ab` aus dem Buchungsblock in die Zeitleiste des Dings? (Empfehlung: ja, nur Darstellung)
- [ ] Muss Terminal am Abflug stehen (Schritt 2, `bei:`) oder reicht die Merkmalliste? (Empfehlung: zuerst Merkmalliste)
- [ ] Soll die Vorlage Art flug die Zeit-Merkmale mitbringen? (Empfehlung: ja, in Schritt 2)

## Änderungen des PO am Entwurf (24.11.2026) — vor /40-tdd-red in die Spec einarbeiten
Spec docs/specs/oberflaeche/zeitleiste-bewegung-665.md wurde automatisch freigegeben, bevor der PO den Entwurf kommentiert hat; sie ist überholt. Nachziehen:
1. Alle Zeiten/Daten gleiche Schriftgröße; Abfahrt/Ankunft nur fetter Name + gefüllter Punkt.
2. Kopfzeile unter dem Titel ohne Art-Namen, nur Datum in Uhrzeit-Größe; abweichendes Datum bei der Uhrzeit, fett, gleiche Größe.
3. Zuordnung eines Merkmals zu einem Zeitpunkt (`bei:` an der Definition) jetzt in Scope; Terminal steht bei der Gepäckabgabe, nicht in der Merkmalliste. Vorlage Art flug bleibt Out of Scope.
4. Atomic Design zwingend (PO): Molekül Zeitleiste aus gemeinsamen Atomen mit halteLeiste; Kopfkommentar, Stile, Bausteinseite, docs/design.md; Test in test_design.py.
Entwurf: docs/context/fix-665-entwurf.html, Artefakt https://claude.ai/artifact/7rvFwhZYkEhJ3mqb5Suez8 (Version 3). Danach spec-validator, po-briefer neu, set-briefing, Freigabe.
