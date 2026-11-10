---
entity_id: rueckmeldung-kontext-449
type: feature
created: 2026-11-10
updated: 2026-11-10
status: draft
workflow: fix-449-rueckmeldung-kontext
version: "1.0"
tags: [oberflaeche, rueckmeldung, kontext, konnektor, adr-0006, eingabeflaeche]
---

# Rückmeldung: Kontext mitspeichern (#449)

Eine Rückmeldung von der Seite bringt einen kleinen, sprachneutralen Kontext mit: in welcher Ansicht, an welchem Abschnitt und bei welchem Reise-Stand die Sprechblase angetippt wurde. Der AI-Client sieht diesen Ort beim Einarbeiten.

## Approval

- [ ] Approved

## Purpose

Dieselbe ID (z. B. eine Option `V-…`) erscheint auf der Seite an mehreren Stellen (Tagesseite, Wahlstelle, Ansicht „Varianten“, Vergleich). Eine Rückmeldung wie „Was ist das?“ lässt sich ohne Ort nicht zuordnen. Mit dem Kontext weiß die Bearbeitung im AI-Client, wo und bei welchem Stand die Frage entstand.

Prüfstelle (ADR-0001): betrifft nur die Eingabefläche (Punkt 7) und die Ablage; keine KI, nichts reisespezifisch, für beide Beispielreisen gleich.

## Source

- **Files:** `engine/vorlage.html`, `engine/rueckmeldungen.py`, `engine/konnektor.py`, `engine/texte_de.py`, `engine/texte_en.py` (die Pseudo-Sprache der Tests liegt in `engine/tests/texte_xx.py`, dort ebenfalls ergänzen), Tests in `engine/tests/`
- **Identifier:** `kontext`, `ansicht`, `abschnitt`, `stand`, `kontext_pruefen`, `rmKontext`

## Prüfung der Annahmen der Analyse (`docs/context/fix-449-rueckmeldung-kontext.md`)

Am Code geprüft, mit diesen Korrekturen:

- Stimmt: Klick auf `[data-rm]` im Dokument-Listener (`engine/vorlage.html`, ~Z. 5459); `rmFormular` (~4886), `rmSpeichern` (~4925, legt `e` an, bei Netzfehler `AUSGANG.push(e)`), `rmAbschicken` (~4940), `senden` (~4847, Body aus festen Feldern `name, art, ziel, text, quelle`), `ausgangSenden` (~4856, ruft `senden(e)` mit dem gespeicherten `e`); `INHALT`, `LAENGE`, `ZIEL_MUSTER`, `pruefen` (`engine/rueckmeldungen.py` ~97 bis 105, 441); Doppelt-Erkennung über `INHALT` (~1316); `liste_text` (`engine/konnektor.py` ~2363); `feedback_give` baut `e` aus `rm.INHALT` (~3025).
- Korrektur: `rmFormular(id)` kennt nur die ID. Der Kontext muss beim Klick festgehalten und dem Dialog mitgegeben werden (z. B. `dlg.dataset.kontext` als JSON); von dort liest ihn `rmAbschicken` und gibt ihn an `rmSpeichern`. Auch die Aufrufe von `rmFormular` aus `rmAbschicken` und `rmNeuZeichnen` (Dialog neu zeichnen) dürfen den Kontext des geöffneten Dialogs nicht verlieren.
- Korrektur: Reiter und Ansicht stehen in der globalen Variable `reiter` (~5735) und im Hash (`location.hash`, in `route` ~5775 mit `decodeURIComponent` gelesen, alte Namen über `routeName` umgesetzt). Als `ansicht` gilt der Hash der Route nach `routeName`, nicht die Variable `reiter` allein (Tagesseiten und Wahlstellen sind Hash-Ziele ohne eigenen Reiter).
- Korrektur: `D.reise_stand.nummer` steckt in der Konstante `RS` (~6045), die `null` sein kann (Seite ohne Stand); dann entfällt `stand`.
- Korrektur: Ein Werkzeug `feedback_show` gibt es nicht. Der Konnektor zeigt Einträge nur in `feedback_list` (Alias von `rueckmeldungen`, `engine/schnittstelle.py` Z. 21). Die zweite Anzeige ist die Befehlszeilenausgabe der Rückmeldungen in `engine/rueckmeldungen.py` (~Z. 1425 bis 1453, je Eintrag Ziel, Text, Quelle, Kommentar); die Stelle ~756 aus der Analyse gehört zu den Wünschen und bleibt unberührt.
- Korrektur: Der Service Worker (`engine/sw.vorlage.js`) bleibt unberührt; die Warteschlange liegt in der Seite (`AUSGANG`, im Browserspeicher als `ausgang`).
- Ebenenklassen im DOM: Abschnitte der Tagesseite tragen `ebene ebene-weg`, `ebene-unterwegs`, `ebene-hintergrund`, `ebene-quellen`, `ebene-nacht`, `ebene-orte` (~Z. 3905 bis 3972); die Tagesseite selbst `tagseite` (~4002). Sprechblasen außerhalb dieser Ebenen haben keinen Abschnitt.

## Dependencies

| Entity | Type | Purpose |
|--------|------|---------|
| `docs/adr/0001-kern.md` | ADR | Prüfstelle, Punkt 7 Eingabefläche |
| `docs/adr/0006-mehrsprachigkeit.md`, `docs/sprachen.md` | ADR | Katalogtexte in allen Sprachen, nie im Code |
| `engine/tests/test_texte.py` | Test | Schlüssel in allen Sprachen, Ausnahmelisten nur kürzer |
| `rm.eintraege` (Wächter, Erinnerer), Datenschutz-Export (#498) | Leser | lesen Einträge unverändert, kein Personenbezug im Kontext |

## Implementation Details

**1. Kontext (sprachneutral).** Ein kleines Objekt `kontext` mit höchstens drei Schlüsseln, nur feste Kennungen, nie Freitext oder Sprache:

| Schlüssel | Bedeutung | Quelle auf der Seite | Muster |
|-----------|-----------|----------------------|--------|
| `ansicht` | Ansicht der Seite beim Klick | Hash der Route nach `routeName` (ohne `#`), z. B. `heute`, `varianten`, `T-03` | `^[A-Za-z0-9][\w.\-]{0,79}$` (wie `ZIEL_MUSTER`) |
| `abschnitt` | Abschnitt der Sprechblase | Name der nächsten Ebene oberhalb des angeklickten Knopfes (`weg`, `unterwegs`, `hintergrund`, `quellen`, `nacht`, `orte`; Klasse `ebene-<name>` ohne Vorsilbe), sonst `tagseite`, wenn nur sie gefunden wird, sonst fehlt der Schlüssel | gleiches Muster, höchstens 40 Zeichen |
| `stand` | Reise-Stand beim Klick | `RS.nummer` (nur die Nummer, kein Zeitstempel; der Bau bleibt deterministisch) | ganze Zahl 1 bis 999999 |

Fehlt eine Angabe (kein Hash, keine Ebene, `RS` ist `null`), bleibt der Schlüssel weg. Sind alle weg, wird kein `kontext` gesendet.

**2. Erfassung beim Klick** (`engine/vorlage.html`). Im Klick-Listener für `[data-rm]` wird der Kontext aus dem angeklickten Knopf und der Route gebildet (kleine Funktion `rmKontext(knopf)`), vor `rmFormular`. `rmFormular(id, kontext)` legt ihn am Dialog ab; Neuzeichnen desselben Dialogs behält ihn. `rmAbschicken` liest ihn aus dem Dialog und reicht ihn an `rmSpeichern(name, art, ziel, text, quelle, kontext)`; dort steht er im Eintrag `e` und damit auch im Offline-Ausgang `AUSGANG`. `senden` schickt `kontext` im Body mit, nur wenn gesetzt. Der Kontext wird beim Klick erfasst, nicht beim Absenden oder Nachreichen: er beschreibt den Ort, an dem die Frage entstand. Einträge im Ausgang, die vor dieser Änderung entstanden sind, haben keinen Kontext und werden wie bisher gesendet.

**3. Dienst** (`engine/rueckmeldungen.py`). `pruefen` bekommt das optionale Feld `kontext` über eine eigene kleine Funktion `kontext_pruefen(roh)`:

- Nur ein Objekt wird angenommen; andere Typen werden verworfen.
- Nur die Schlüssel `ansicht`, `abschnitt`, `stand`; alle anderen Schlüssel werden verworfen.
- Je Schlüssel Typ, Muster und Länge wie in der Tabelle; ein abweichender Wert wird verworfen, die übrigen gültigen Teile bleiben.
- Bleibt nichts Gültiges, wird kein `kontext` im Eintrag abgelegt.
- Die Antwort ist in jedem Fall dieselbe wie ohne Kontext (kein Fehler wegen des Kontexts).
- `INHALT` bleibt unverändert: der Kontext gehört nicht zur Doppelt-Erkennung (~Z. 1316) und nicht zu `feedback_give` (das über `rm.INHALT` baut). Dieselbe Rückmeldung innerhalb von `DOPPELT_SEKUNDEN` bleibt ein Doppelt-Treffer, auch wenn der Kontext abweicht; die erste Ablage bleibt bestehen.
- `MAX_BODY` (16 KiB) und die Mengenbegrenzung bleiben wirksam.

**4. Ablage.** Der Eintrag in `eingang.jsonl` trägt zusätzlich `"kontext": {…}`. Alte Einträge ohne das Feld bleiben gültig; Leser nehmen `e.get("kontext")`. Eine Umstellung der Reisedaten (`neu.py nachziehen`) ist nicht nötig, weil das Feld optional ist und kein bestehendes Format ändert.

**5. Anzeige im Konnektor** (`engine/konnektor.py`, Texte in `engine/texte_*.py`). `liste_text` hängt unter dem Eintrag (nach der Textzeile) eine Zeile „Ort“ an, wenn ein Kontext da ist, z. B. de: „  Ort: Ansicht {ansicht}, Abschnitt {abschnitt}, Reise-Stand {stand}“; fehlende Teile entfallen samt Beschriftung. Beschriftungen als neue Katalogschlüssel (z. B. `konnektor.rueckmeldungen.kontext` mit Teilen für Ansicht, Abschnitt, Stand) in allen Sprachen (`texte_de.py`, `texte_en.py`, Pseudo-Sprache der Tests). Die Werte selbst (Kennungen, Zahl) werden nicht übersetzt. Dieselbe Zeile steht in der Befehlszeilenausgabe der Rückmeldungen (`rueckmeldungen.py` ~Z. 1451); ohne Kontext bleibt diese Ausgabe unverändert. `feedback_give` bleibt unverändert: die KI-Seite hat keinen Seitenkontext, das Feld ist optional und wird dort nicht angenommen, auch kein neuer Alias in `schnittstelle.py`.

## Abweichung vom Issue: verwerfen statt abweisen

Das Issue sagt: „Dienst nimmt ihn an bzw. **weist ungültigen ab**.“ Diese Spec entscheidet anders: **ein ungültiger Kontext wird still verworfen, die Rückmeldung selbst wird trotzdem angenommen.**

Begründung: Der Kontext ist ein Zusatz, die Rückmeldung der Zweck. Eine Abweisung würde eine sonst gültige Rückmeldung verlieren: die Seite verwirft abgelehnte Einträge (`ausgangSenden` überspringt bei `abgelehnt`, der Eintrag verschwindet aus dem Ausgang). Eine Rückmeldung geht nie verloren; ein älterer oder fehlerhafter Client mit anderem Kontext-Format darf keine Eingabe blockieren. Die Eingabe bleibt trotzdem geschützt, weil nur feste Schlüssel, Muster und Längen in den Eintrag gelangen. „Abweisen“ aus dem Issue ist damit als „nicht ablegen“ zu lesen. Die Tests belegen beides (AC-4, AC-5).

## Architektur-Entscheidung (ADR)

**ADR-Nr.:** ADR-0001 (Prüfstelle, Punkt 7 Eingabefläche), ADR-0006 (Mehrsprachigkeit, Texte im Katalog). Keine neue Architektur-Entscheidung nötig: additives, optionales Feld ohne Format-Umstellung.

## Expected Behavior

- **Input:** Tippen auf eine Sprechblase (`[data-rm]`), Text eingeben, Senden; auch ohne Netz.
- **Output:** Eintrag mit `kontext` (nur gültige Teile); `feedback_list` zeigt den Ort lesbar in der Sprache des Aufrufers.
- **Side effects:** keine; kein neuer Dienst, keine KI, keine Umstellung bestehender Reisen.

## Acceptance Criteria

- **AC-1:** Given die gebaute Seite der Beispielreise (Wanderung) / When eine Sprechblase auf einer Tagesseite im Abschnitt „Weg“ angetippt wird / Then bildet `rmKontext` `{ansicht: <Hash der Tagesseite>, abschnitt: "weg", stand: <Nummer>}`; derselbe Knopf in der Ansicht „Varianten“ liefert die dortige Ansicht und keinen Abschnitt einer Tagesseite.
- **AC-2:** Given das Städtewochenende (ohne Varianten, ohne Wanderung) / When eine Sprechblase einer Tagesseite oder die „Allgemeine Rückmeldung“ angetippt wird / Then ist der Kontext gültig und enthält nur Teile, die es dort gibt (bei „allgemein“ im Reiter Rückmeldungen: `ansicht`, `stand`, kein `abschnitt`); kein Fehler, wenn die Reise keine Varianten hat.
- **AC-3:** Given eine Seite ohne Reise-Stand (`RS` ist `null`) / When gesendet wird / Then fehlt `stand` im Kontext, ohne Fehler; sind alle Teile leer, geht der Body ohne `kontext`-Feld.
- **AC-4:** Given der Dienst / When `POST` einen gültigen Kontext enthält (`ansicht`, `abschnitt`, `stand`) / Then wird die Rückmeldung angenommen und der Eintrag in `eingang.jsonl` trägt genau diesen Kontext.
- **AC-5:** Given der Dienst / When der Kontext ungültig ist (kein Objekt, fremder Schlüssel, Muster verletzt, zu lang, `stand` keine Zahl oder ≤ 0 oder zu groß, verschachtelte Werte) / Then wird die Rückmeldung trotzdem mit derselben Antwort wie ohne Kontext angenommen, aber ohne die ungültigen Teile (gültige Restteile bleiben, fremde Schlüssel nie); kein Fehlertext wegen des Kontexts.
- **AC-6:** Given zwei Rückmeldungen mit gleichem `INHALT` und verschiedenem Kontext innerhalb von `DOPPELT_SEKUNDEN` / When beide gesendet werden / Then bleibt es ein Doppelt-Treffer (ein Eintrag); `rm.INHALT` ist unverändert (`name, art, ziel, text, quelle`).
- **AC-7:** Given alte Einträge ohne `kontext` in `eingang.jsonl` / When `rm.eintraege`, `feedback_list`, die Befehlszeilenausgabe, Wächter, Erinnerer und Export sie lesen / Then funktioniert alles wie bisher; `feedback_list` und die Befehlszeilenausgabe zeigen für sie keine „Ort“-Zeile, die Ausgabe ist Zeichen für Zeichen gleich der Ausgabe vor der Änderung (Vergleichstest mit festem Soll-Text).
- **AC-8:** Given Offline (`senden` schlägt mit Netzfehler fehl) / When die Rückmeldung später aus `AUSGANG` nachgereicht wird / Then trägt sie den Kontext vom Klick, auch wenn dann eine andere Ansicht offen ist; `senden` schickt `kontext` aus dem Eintrag mit.
- **AC-9:** Given ein Eintrag mit Kontext / When `feedback_list` aufgerufen wird / Then steht unter dem Eintrag eine Zeile „Ort“ mit Ansicht, Abschnitt und Stand; für `de`, `en` und die Pseudo-Sprache der Tests mit den Beschriftungen aus dem Katalog, die Werte unübersetzt; fehlende Teile entfallen samt Beschriftung. Die Befehlszeilenausgabe zeigt denselben Ort.
- **AC-10:** Given `feedback_give` / When es aufgerufen wird / Then ist Verhalten und Parametersatz unverändert (kein Kontext-Parameter, kein neuer Alias); der Eintrag hat keinen `kontext`.
- **AC-11:** Given der Textkatalog / When `engine/tests/test_texte.py` läuft / Then sind die neuen Schlüssel in allen Sprachen vorhanden, die Ausnahmelisten nicht länger geworden; im Code steht kein neuer sichtbarer Text.
- **AC-12:** Given der Gesamtlauf / When `engine/.venv/bin/python -m pytest -q engine/tests` (mit `-n 3`) läuft / Then ist er grün, ohne echte Reisen; der Bau beider Beispielreisen bleibt deterministisch (zweimal bauen, gleiche Ausgabe).

## Test Plan

Erst rot, dann Umsetzung:

- `engine/tests/test_rueckmeldungen.py` (Dienst, ohne Browser): AC-4, AC-5 (parametrisierte Tabelle ungültiger Fälle, Grenzfälle Länge, Muster, `stand`), AC-6, AC-7.
- Seite: die vorhandene Art, die gebaute Seite mit Skript auszuführen (wie bei den Tests zur Startfehler-Meldung #387; vorher nachsehen, welche Testhilfen es gibt): AC-1 und AC-2 an beiden Beispielreisen, AC-3, AC-8 (Netz gesperrt, Eintrag im Ausgang mit Kontext, später nachgereicht).
- Konnektor-Tests (Muster der vorhandenen Tests für `liste_text`): AC-9 in `de`, `en`, Pseudo-Sprache; AC-10.
- `engine/tests/test_texte.py`: AC-11 unverändert strikt.
- Eine Abnahme über den Konnektor mit Testreise ist nicht nötig (keine KI-Funktion, Anzeigezeile durch Tests belegt); beide Reisetypen sind durch AC-1 und AC-2 abgedeckt.

## Known Limitations

- Der Abschnitt kennt nur die festen Ebenen der Tagesseite; Sprechblasen an anderer Stelle tragen nur Ansicht und Stand.
- Der Reise-Stand ist der Stand der geladenen Seite, nicht der des Servers; bei veralteter Offline-Seite zeigt er genau das, was die Person sah (gewollt).
- Der Kontext kommt vom Gerät und ist nur formal geprüft, nicht überprüfbar.

## Scope

- Files: 5 (`vorlage.html`, `rueckmeldungen.py`, `konnektor.py`, `texte_de.py`, `texte_en.py`) plus Pseudo-Sprache und Tests
- Geschätzte LoC: +120/-5
- Risiko: LOW (additiv, optionales Feld); Hauptrisiken Doppelt-Erkennung und `senden` mit festen Feldern sind durch Tests belegt.

## Definition of Done

- [ ] AC-1 bis AC-12 erfüllt, Pflichtprüfungen grün (`tests (leer)`, `tests (instanz)`, `gitleaks`)
- [ ] Prüfstelle (ADR-0001) im PR-Template beantwortet; Abweichung „verwerfen statt abweisen“ im PR und in #449 benannt
- [ ] Ändert der PR Meldungstexte oder Schnittstellen: Tests der einbindenden Instanzen laufen vor dem Vorspulen mit dem Branch
- [ ] #449 erst geschlossen, wenn alles end to end erledigt ist

## Rückweg

Kontext-Erfassung in der Seite und die Zeile im Konnektor entfernen; bereits abgelegte `kontext`-Felder bleiben harmlos in `eingang.jsonl` (Leser ignorieren unbekannte Felder).

## Changelog

- 2026-11-10: Erstfassung (#449); Abweichung vom Issue (verwerfen statt abweisen) und Korrekturen an der Analyse festgehalten
