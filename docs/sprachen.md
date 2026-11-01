# Sprachen: Texte der Software und eine neue Sprache hinzufügen

Entscheidung: [ADR-0006](adr/0006-mehrsprachigkeit.md). Plan und Hintergründe: [mehrsprachigkeit.md](mehrsprachigkeit.md). Stand 31.10.2026.

Frieda spricht Deutsch und Englisch. Jede weitere Sprache ist **eine Datei** `engine/texte_<kürzel>.py`; im Code steht keine Sprache beim Namen. Seite, Umschalter, Kontoseite, `Accept-Language`, Konnektor, Mails, Kalender und Wächter kennen die Sprache ab dem Moment, in dem die Datei neben dem Code liegt.

## Wer welche Sprache spricht

| Wer | Quelle | Vorgabe | Setzen |
|---|---|---|---|
| Seite (Startwert), Manifest, Kalender, Wächter-Meldungen, alles, was die Software in Dateien der Reise schreibt, Commit-Nachrichten | `reise.yaml`, Feld `sprache` | `de` | `trip_create` (Parameter `language`, Vorgabe: Sprache des Kontos), `setting_set` (nur Organisator:innen, mit Grund) |
| Seite (Hülle) nach dem Umschalten | `localStorage` der Person | Sprache der Reise | Umschalter auf der Seite |
| Konnektor (Anleitung, Beschreibungen, Ergebnisse, Fehler), Kontoseiten, Mails an die Person | Spalte `konten.sprache` | aus `Accept-Language` beim Anlegen des Kontos, sonst `en` | Kontoseite, Werkzeug `language_set` |
| Einladung an eine Adresse ohne Konto | Sprache der Reise | | |
| Rückmeldedienst | Feld `sprache` der Anfrage | Sprache der Reise | die Seite schickt ihre Sprache, der Konnektor die der Person |

Der Umschalter ändert nur die Hülle der Seite (Beschriftungen, Datum, Zahlen, Sortierung). Der Inhalt der Reise bleibt in der Sprache, in der er geschrieben ist.

## Was nie übersetzt wird

Datenschlüssel in YAML und JSON (`art`, `quelle`, `geprueft`, `gilt`, `status` …), Werte mit fester Bedeutung (`gewaehlt`, `verworfen`, `gebucht`, `offen`, `organisator` …), ID-Präfixe (`T-`, `E-`, `U-` …), Dateinamen der Reise, Pfade des Schreibwegs, Namen von Arten, Merkmalen, Kategorien, Titel, Gründe und alle Inhalte der Reise. Wo ein englischer Text einen solchen Wert nennt, wird er erklärt, nicht übersetzt („status `gewaehlt` (chosen)“). Für den Konnektor nehmen die Aufrufe auch englische Namen und Aliase an ([konnektor.md](konnektor.md), „Englische Namen der Schnittstelle“).

## Eine Sprache hinzufügen

1. **Datei anlegen:** `engine/texte_<kürzel>.py` (zwei oder drei Kleinbuchstaben, zum Beispiel `fr`). Am einfachsten wird `texte_en.py` kopiert und übersetzt. Die Felder stehen unten. Der Test `test_texte.py` nennt, was an Schlüsseln oder Platzhaltern fehlt.
2. **Prüfen, dass sie gefunden wird:** `texte.SPRACHEN` liest die Dateien `texte_*.py` neben `texte.py` (Deutsch und Englisch zuerst, dann nach dem Alphabet). Es gibt keine Liste, in die das Kürzel einzutragen wäre; `betrieb/deploy.sh` nimmt jede Sprachdatei von selbst mit auf den Server.
3. **Optional die Reisevorlage:** `engine/reisevorlage/<kürzel>/` (Überschriften und Gerüst einer neuen Reise in dieser Sprache; fehlt der Ordner, nimmt `neu.py` die englische) und ein `README.<kürzel>.md`.
4. **Tests laufen lassen:** `engine/.venv/bin/python -m pytest -q engine/tests`. Parität der Kataloge, Rundgang im Browser je Sprache, Konnektor je Sprache und die Literal-Tests laufen über `texte.SPRACHEN` und nehmen die neue Sprache mit. Mehr ist nicht zu tun.

Eine Sprache, deren Datei einen Schlüssel nicht hat, fällt für diesen Text auf Englisch zurück; ein Absturz wegen eines Textes gibt es nicht. Der Paritätstest verlangt trotzdem alle Schlüssel.

## Felder einer Sprachdatei

| Feld | Bedeutung |
|---|---|
| `NAME` | Name der Sprache in ihr selbst („Deutsch“, „English“); steht auf dem Umschalter und in der Auswahl der Kontoseite |
| `LOCALE` | Locale für `Intl` im Browser und für Zahlen (`de-DE`, `en-GB`, `ar-EG`) |
| `RICHTUNG` | `ltr` oder `rtl`; die Seite setzt `dir` am Dokument, die Stile nutzen logische Eigenschaften |
| `PLURAL` | Funktion `n -> Kategorie` nach CLDR (`zero`, `one`, `two`, `few`, `many`, `other`) |
| `DATUM`, `DATUM_KURZ`, `ZEIT`, `DATUM_ZEIT` | `strftime`-Formen für Datum mit und ohne Jahr, Uhrzeit und Zeitpunkt (Deutsch `%-d.%-m.%Y`, Englisch `%-d/%-m/%Y`) |
| `WOCHENTAGE_KURZ` | sieben Kurzformen, Montag zuerst (der Rechner-Locale ist nicht zuverlässig) |
| `TEXTE` | Wörterbuch Schlüssel -> Text |

## Regeln für Schlüssel und Texte

- Schlüssel sind flach, in Kleinbuchstaben, mit Punkten getrennt, der Bereich steht vorn: `seite.`, `konnektor.`, `schreiben.`, `dienst.`, `konto.`, `mail.`, `kalender.`, `waechter.`, `inhalt.`, `pruefung.` (Prüfmeldungen der Reise), `wert.` und `symbol.` (Datenwerte der Reise, siehe unten). Der Test prüft die Form.
- Platzhalter haben Namen in geschweiften Klammern (`{name}`, `{n}`, `{id}`), nie Positionen, und sind in allen Sprachen dieselben.
- Jeder Text ist ein ganzer Satz oder eine ganze Beschriftung. Nichts wird aus Teilen zusammengesetzt (`"Nacht in " + ort` wird ein Schlüssel mit `{ort}`), damit andere Sprachen die Wortstellung ändern können. Ausnahme: Bestätigungen des Schreibwegs sind aus Sätzen des Katalogs zusammengesetzte `Satz`-Folgen, die in jeder Sprache gebaut werden können (`texte.Satz`).
- Plural nur über Kategorien: gibt es den Wert `n`, wählt `PLURAL` die Kategorie, und `t()` nimmt `<schluessel>.<kategorie>`, dann `<schluessel>.other`, dann `<schluessel>`. Deutsch und Englisch füllen `.one` und `.other`, nie `n == 1 ? … : …` im Code.
- Datenwerte bleiben, wie sie sind; Texte der Reise gehören nicht in den Katalog (ADR-0001).
- Deutsche Texte bleiben Zeichen für Zeichen, wie sie sind. Englische Texte: kurz, klar, in der Du-Form („you“), britische Schreibung.
- Wörter, an denen die Software Inhalte der Reise erkennt (Überschriften wie „Übersicht“, „Quellen“, Fragestatus), stehen unter `inhalt.` und gelten in allen Sprachen zugleich (`texte.inhaltswoerter`), damit eine Reise in jeder Sprache erkannt wird.
- Im Code: `t(kuerzel, schluessel, **werte)` für Texte; der Konnektor nimmt `tk()` (Sprache des Aufrufs) und `tkd()` (immer Deutsch, für Text, der in der Reise gespeichert wird). Ein Text, den eine Person liest, kommt aus dem Katalog; Text, der in die Reise geschrieben wird, in der Sprache der Reise.

## Verbote im Code

Der Literal-Test und der Grep-Test in `engine/tests/test_texte.py` prüfen bei jedem Lauf:

- keine deutschen Literale mit Umlauten oder ß im Code der Dateien, die Personen etwas zeigen (die Ausnahmelisten dürfen nur kürzer werden; was in Dateien der Reise geschrieben wird, bleibt dort aufgeführt);
- keine Sprache beim Namen: kein `if sprache == "de"`, keine festen Locale-Strings (`"de-DE"`), keine Wochentags- oder Monatslisten, keine feste Zahl von Sprachknöpfen;
- kein `one/other` als einzige Pluralfrage.

Datum, Zeit und Zahl kommen aus der Sprachdatei (`texte.datum`, `texte.datum_kurz`, `texte.zeit`, `texte.wochentag`) beziehungsweise im Browser aus `Intl` mit der `LOCALE` der Sprache.

## Die Pseudo-Sprache

`engine/tests/texte_xx.py` ist eine Sprache nur für Tests. Sie hat absichtlich andere Eigenschaften als Deutsch und Englisch: Locale `ar-EG` (andere Ziffern), Schreibrichtung `rtl`, sechs Pluralkategorien, jeder Text als `[xx …]` markiert. Die Tests laden sie mit der Umgebungsvariablen `FR_TEXTE_ZUSATZ=xx`, bauen die Beispielreise mit `sprache: xx` und prüfen `lang`, `dir`, markierte Texte, Plural mit `few`, Datum und Zahl der Locale, drei Knöpfe im Umschalter und markierte Beschreibungen im Konnektor. Sie beweist bei jedem Lauf, dass eine neue Sprache eine Datei ist und keine Codeänderung: Bleibt irgendwo ein deutscher oder englischer Text im Code, fällt er in der Pseudo-Sprache auf.

## Tests, die den Umbau tragen

- `test_texte.py`: Parität (gleiche Schlüssel und Platzhalter in allen Sprachen), Rückfall, Plural nach Kategorien, `aus_header`, Pflichtfelder, Form der Schlüssel, Pseudo-Sprache, Literal- und Grep-Test, Sprachdateien im Deploy.
- `test_seite_sprachen.py`: Rundgang im Browser je Sprache in `texte.SPRACHEN` und das Umschalten.
- `test_konnektor.py`, `test_schreiben.py`, `test_kalender.py`, `test_waechter.py`: englische Stichproben (Konto `en`, englische Reise).

## Noch offen (Stand 31.10.2026)

Die Ausnahmelisten in `test_texte.py` sind noch nicht leer. Was bleibt, sieht eine Person kaum oder nur über Betreiber:

- **Texte, die in Dateien der Reise geschrieben werden** (Kopfkommentare der Dateien, Verlaufseinträge, Commit-Nachrichten in `schreiben.py`, `neu.py`): bleiben bewusst deutsch beziehungsweise in der Sprache der Reise, weil sie zum Bestand der Reise gehören.
- **Ausgaben für Betreiber auf der Kommandozeile** (`konnektor.py`, `rueckmeldungen.py`, `waechter.py`, `konten.py`, `bauen.py`, `neu.py`: Startmeldungen, Hilfetexte, Protokollzeilen).
- **Muster und Datenwerte** (Zeichenklassen mit Umlauten in regulären Ausdrücken, Art `Ergänzung` einer Rückmeldung, `geändert`, `Geprüft`, ein Dossier-Titel) und zwei Treffer in der Vorlage.

## Prüfmeldungen der Reise

Fehler und Hinweise der Prüfung beim Bauen („Unterkunft U-01: Ort O-09 gibt es nicht.“) stehen als Sätze unter `pruefung.<bereich>.<nummer>` im Katalog und werden im Code mit `texte.satz("pruefung.routen.6", …)` erzeugt. Als Text ist ein solcher Satz der Wortlaut im Rückfall der Software (`texte.VORGABE_REISE`, Englisch; Bau-Protokoll, Tests); er trägt Schlüssel und Werte mit, sodass der Konnektor ihn in der Sprache der Person setzt: Eine Ablehnung des Probebaus (`schreiben.bau.nichts_geaendert`) und die Hinweise nach einem Eintrag (`hinweise_teile`) reisen mit ihren Schlüsseln zum Konnektor. Werte berechneter Merkmale, die die Seite zeigt (Anschluss zwischen Optionen, Hinweis „Lage fehlt“), folgen der Sprache der Reise (`Routen.sprache`).

## Rückfall und Bestand

- `texte.VORGABE_REISE` (Englisch) ist die Sprache der Software, wo keine Sprache bekannt ist: Protokolle, Fehlertexte ohne Person, unbekannte Sprache. Lieber Englisch bei einer Person, die es nicht erwartet, als Deutsch bei einer anderen.
- `texte.BESTAND_REISE` (Deutsch) gilt nur für eine `reise.yaml` ohne Feld `sprache:` (Reisen von vor ADR-0006). Die Software schreibt nichts in fremde Reisen; sie liest das fehlende Feld als `de`. Neue Reisen tragen `sprache:` immer in der Datei.
- Die Tests laufen mit einer Pinnung auf Deutsch (`engine/tests/conftest.py`), weil sie deutsche Wortlaute prüfen; Tests mit `@pytest.mark.echter_rueckfall` und der Schreibdienst im Unterprozess sehen den echten Rückfall.

## Was in Dateien der Reise landet
- Was die Software in Dateien einer Reise schreibt, folgt der Sprache der Reise (`reise.sprache_von`): Herkunftszeilen an Wissensabschnitten (`inhalt.schreiben.herkunft.*`), die Kopfkommentare von `plan/arten.yaml` und `plan/kategorien.yaml` (`inhalt.schreiben.*_kopf`), der Status in `offene-fragen.md`. Die Texte stehen unter `inhalt.*` im Katalog, das Datum kommt aus `texte.datum(datum, sprache)`.
- Antwortsätze an die Person tragen Daten als Wert `texte.Datum` (oder `texte.DatumKurz` ohne Jahr), nicht als fertigen Text: Der Satz formatiert sie erst in der Sprache, in der er gelesen wird, auch auf dem Weg vom Dienst zum Konnektor (`{"datum": "JJJJ-MM-TT"}`). Kein `strftime` mit festem Muster in Texten.
- Titel, Text und Fuß der Commits stehen in der Sprache der Reise, ebenso der Verlauf. Werkzeug- und Parameternamen darin sind die englischen der Schnittstelle (`schreiben.am_rand`), außer eine Sprache erklärt deutsche Aliasse (`inhalt.schreiben.werkzeug_alias`).

### Datenwerte

Gespeichert wird immer der Datenwert selbst (`organisator`, `gewaehlt`, `blau`, `auswahl`; ADR-0006). Wer ihn **liest**, bekommt ihn in seiner Sprache: Jeder Wert eines Platzhalters, der genau einem Eintrag `wert.<Wert>` des Katalogs entspricht, wird von `texte.t` (und damit von jedem Satz) durch dessen Text ersetzt, bei fehlender Übersetzung durch den englischen. Deutsch zeigt den Wert unverändert (`"wert.organisator": "organisator"`). Ein neuer Datenwert (Rolle, Stufe, Farbe, Typ, Baustein, Schlüssel der Spielregeln) braucht deshalb einen Eintrag `wert.*` in jeder Sprache. Nicht hinein gehören Wörter, die im Englischen genauso lauten (`text`, `plan`, `bus`): sie brauchen keine Übersetzung. Wo der Code Werte selbst aneinanderhängt (f-String, `", ".join(...)`), bleibt der deutsche Wert stehen: dafür gibt es einen Satz im Katalog (`schreiben.antwort.feld_wert`) oder `schreiben.anzeige_text`. Der Test `test_englisch.py` fängt jede Stelle, an der ein deutscher Wert durchrutscht.
