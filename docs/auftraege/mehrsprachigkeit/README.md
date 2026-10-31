# Aufträge Mehrsprachigkeit: Grundregeln für alle Pakete

Plan: `docs/mehrsprachigkeit.md` · Entscheidung: `docs/adr/0006-mehrsprachigkeit.md` · Kern: `docs/adr/0001-kern.md`

Jede Datei `M*.md` in diesem Ordner ist ein vollständiger Auftrag für einen Agenten (Haiku oder Sonnet, steht im Kopf). Der Auftrag an den Agenten lautet wörtlich:

> Führe den Auftrag `docs/auftraege/mehrsprachigkeit/M0.md` aus. Lies zuerst `docs/auftraege/mehrsprachigkeit/README.md` und halte dich an alles darin.

## Stand

| Paket | Titel | Modell | Voraussetzung | Status |
|---|---|---|---|---|
| M0 | Katalog und Leitplanken | Haiku | – | umgesetzt (31.10.2026) |
| M1 | Sprache der Reise, Startwert der Seite, Umschalter | Haiku | M0 | umgesetzt (31.10.2026) |
| M2 | Datum, Zahl, Sortierung, Karte | Sonnet | M1 | umgesetzt (31.10.2026) |
| M3 | Vorlage A: Rahmen, Reiter, Suche, Plan, Tag, Etappe | Haiku | M2 | offen |
| M4 | Vorlage B: Varianten, Wahl, Buchung, Karte, Unterkunft | Haiku | M2 | offen |
| M5 | Vorlage C: Wissen, Fragen, Aufgaben, Wünsche, Rückmeldungen, Konto, Bausteinseite | Haiku | M2 | offen |
| M6 | Inhaltserkennung sprachfest, Reisevorlage je Sprache | Sonnet | M5 | offen |
| M7 | Sprache am Konto | Haiku | M0 | offen |
| M8 | Konnektor: Anleitung und Beschreibungen | Haiku, dann Sonnet | M7 | offen |
| M8b | Englische Namen der Schnittstelle mit Aliasen | Sonnet, dann Haiku | M8 | offen |
| M9 | Fehler als Schlüssel: Schreibweg, Regeln, Rückmeldedienst | Sonnet, dann Haiku (vier Stapel) | M8b | offen |
| M10 | Konnektor-Ergebnisse, Kalender, Wächter | Haiku | M8b | offen |
| M11 | Dokumentation und Abschluss | Haiku | M6, M9, M10 | offen |
| M12 | Abnahme und dritte Sprache | Sonnet | M11 | offen |

Wer ein Paket startet, trägt hier „läuft“ ein, wer es übernimmt, „übernommen (Datum)“.

## Rolle

Du arbeitest an der Software Frieda Reist (öffentliches Repo, AGPL-3.0). Du setzt genau ein Paket um, nicht mehr. Du triffst keine Architekturentscheidungen; die stehen in ADR-0006 und im Plan. Wo der Auftrag eine Frage offen lässt, wählst du die kleinste Lösung, die der Plan zulässt, und schreibst sie in die PR-Beschreibung unter „Offen“.

## Regeln, die in jedem Paket gelten

1. **Deutsch bleibt wörtlich gleich.** Jeder deutsche Text wandert Zeichen für Zeichen in den Katalog (Leerzeichen, Anführungszeichen „“, Satzzeichen, Auslassungspunkte …). Keine Umformulierung, keine Korrektur, auch wenn ein Text unglücklich wirkt. Die rund 440 Teilstring-Prüfungen in `engine/tests/` sind die Kontrolle: Sie müssen ohne Änderung grün bleiben. Fällt eine, hast du Deutsch verändert.
2. **Was nie übersetzt und nie umbenannt wird:** Datenschlüssel in YAML und JSON (`art`, `quelle`, `geprueft`, `gilt`, `status` …), Enum-Werte (`gewaehlt`, `verworfen`, `ersetzt`, `vorgeschlagen`, `favorisiert`, `organisator`, `mitwirkend`, `gast`, `pflicht`, `empfohlen`, `angeboten`, `aus`, `idee`, `planung`, `fest`, `unterwegs`, `danach`, `archiv`, `offen`, `in_arbeit`, `erledigt`, `entfaellt`, `gebucht`, `angefragt`, `storniert`, `geklaert`, die `ARTEN` der Rückmeldungen `Kommentar`, `Frage`, `Korrektur`, `Ergänzung`, `Antwort`, `Wunsch`), ID-Präfixe (`T-`, `E-`, `O-`, `U-`, `A-`, `B-`, `V-`, `P-`, `F-`, `W-`, `AG-`, `R-`), Dateinamen der Reise (`reise.yaml`, `plan/routen.yaml`, `plan/arten.yaml`, `offene-fragen.md` …), Pfade des Schreibwegs, interne Werkzeugnamen in `schreiben.py` und `rueckmeldungen.py`, Namen von Arten, Merkmalen, Kategorien, Auswahlwerte, Wissen, Lesetexte, Titel, Gründe der Reise. Bezeichner im Code (Funktionen, Variablen, Kommentare) bleiben deutsch (`CLAUDE.md`).
3. **Katalog:** `engine/texte_de.py` und `engine/texte_en.py` haben dieselben Schlüssel. Schlüssel flach, Kleinbuchstaben, Punkte als Trenner, Bereich vorn: `seite.`, `konnektor.`, `schreiben.`, `dienst.`, `konto.`, `mail.`, `kalender.`, `waechter.`, `inhalt.`. Platzhalter mit Namen in geschweiften Klammern (`{name}`, `{n}`, `{id}`), nie positional. Jeder Text ist ein ganzer Satz oder eine ganze Beschriftung; nichts wird aus Teilen zusammengesetzt (`"Nacht in " + ort` wird ein Schlüssel mit `{ort}`). Plural über Kategorien `.zero`, `.one`, `.two`, `.few`, `.many`, `.other` (Deutsch und Englisch füllen `.one` und `.other`), nie über `n === 1 ? … : …`. Englische Texte sind kurz, klar, in der Du-Form wie das Deutsche („you“), britische Schreibung; Datenwerte, die in einem englischen Text vorkommen, werden erklärt, nicht übersetzt („status `gewaehlt` (chosen)“).
4. **Keine Sprache beim Namen im Code:** kein `if sprache == "de"`, keine festen Locale-Strings (`"de-DE"`), keine Wochentags- oder Monatslisten, keine feste Zahl von Sprachknöpfen. Alles, was eine Sprache ausmacht, steht in ihrer Datei (`NAME`, `LOCALE`, `RICHTUNG`, `PLURAL`, `DATUM`, `DATUM_KURZ`, `ZEIT`, `TEXTE`). Listen laufen über `texte.SPRACHEN`. Der Grep-Test aus M0 prüft das.
5. **Ausnahmelisten kürzen:** Der Literal-Test in `engine/tests/test_texte.py` führt je Datei die noch erlaubten deutschen Literale. Dein Paket entfernt die Einträge seines Bereichs. Neue Einträge sind verboten.
6. **Kein KI-Lauf in Frieda, kein Katalog von Arten oder Merkmalen** (ADR-0001). Der Textkatalog enthält nur Wörter der Software.
7. **Bausteine (ADR-0002):** Ein neuer Baustein der Vorlage steht an vier Stellen (Kopfkommentar „Bausteine nach Ebenen“, Stile seiner Ebene, Bausteinseite, `docs/design.md`); `test_design.py` prüft das. Vorhandene Bausteine nutzen (`umschalter`), keine neuen Stile ohne Not. Jede Grundform hat genau eine Heimat (ADR-0003).
8. **Module der Dienste:** Ein neues Modul, das Konnektor, Rückmeldedienst oder Schreibweg importieren, steht in `betrieb/deploy.sh` (`KN_MODULE`, `RM_MODULE`, `SB_MODULE`) und in `CODE_DATEIEN` in `engine/konnektor.py`; `test_betrieb.py` prüft das.
9. **Sprache der Arbeit:** Deutsch mit korrekten Umlauten in Code, Kommentaren, Commits, PR.

## Tests

```bash
python3 -m venv engine/.venv && engine/.venv/bin/pip install -q -r engine/requirements.txt
```

```bash
engine/.venv/bin/python -m pytest -q engine/tests
```

Alles muss grün sein. Einzige zulässige Ausnahme: Browser-Tests mit der Variante `[webkit]`, wenn in der Umgebung kein WebKit installiert ist (Fehler `browserType.launch` oder `Executable doesn't exist`); die Variante `[chromium]` derselben Tests muss bestehen. Das steht dann so in der PR-Beschreibung. Vor dem Umbau einer Ansicht läuft der Rundgang einmal mit DOM-Datei (`seiten_browser.mjs … <dom-datei>`), nach dem Umbau noch einmal; der Vergleich zeigt, ob Deutsch gleich geblieben ist.

## Abgabe

- Branch `claude/mehrsprachigkeit-<paket>` (etwa `claude/mehrsprachigkeit-m3`), abgezweigt vom aktuellen `main`. Kleine, thematisch saubere Commits auf Deutsch.
- Pull Request gegen `main` mit dem PR-Template (`.github/pull_request_template.md`, Prüfstelle ADR-0001 vollständig ausgefüllt). Unter „Was ändert sich“ zwei Sätze für den Product Owner in einfachen Worten; unter „Tests“ das Ergebnis des Testlaufs und die Zahl der entfernten Einträge aus der Ausnahmeliste.
- Nichts nach `main` pushen, nichts zusammenführen; das macht die Sitzung, die den Auftrag vergeben hat, nach eigener Prüfung.
- Keine Dateien außerhalb des Pakets anfassen. Fällt dir etwas außerhalb auf, steht es im PR unter „Offen“, nicht im Code.
- Am Ende in dieser Datei die Statuszeile des Pakets auf „läuft (PR #…)“ setzen.
